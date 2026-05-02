"""NIR web intake service for PDF upload and case creation.

Orchestrates the creation of cases originating from the NIR web
upload surface, including PDF storage, audit trail persistence,
and downstream processing job enqueue.

This service replaces the Matrix-based Room-1 intake for web-origin
cases while preserving the same downstream processing pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from triage_automation.application.ports.audit_repository_port import (
    AuditEventCreateInput,
    AuditRepositoryPort,
)
from triage_automation.application.ports.case_repository_port import (
    CaseRepositoryPort,
    WebCaseCreateInput,
)
from triage_automation.application.ports.job_queue_port import JobEnqueueInput, JobQueuePort
from triage_automation.application.ports.pdf_storage_port import PdfFileStoragePort
from triage_automation.domain.case_status import CaseStatus
from triage_automation.domain.web_event_contract import (
    WebEventOrigin,
    WebEventType,
    WebHumanEvent,
)

logger = logging.getLogger(__name__)


class NirWebIntakeValidationError(ValueError):
    """Raised when the submitted PDF fails deterministic validation."""


@dataclass(frozen=True)
class NirWebIntakeResult:
    """Outcome of a web PDF intake operation."""

    processed: bool
    case_id: str | None = None
    reason: str | None = None


# Accepted MIME types for PDF uploads.
_ACCEPTED_MIME_TYPES: frozenset[str] = frozenset({"application/pdf"})

# Accepted file extensions for PDF uploads (lowercase, with dot).
_ACCEPTED_EXTENSIONS: frozenset[str] = frozenset({".pdf"})


def _validate_pdf_upload(
    *,
    pdf_bytes: bytes | None,
    filename: str | None,
    content_type: str | None,
) -> None:
    """Deterministic validation of the uploaded PDF.

    Args:
        pdf_bytes: Raw file content, or None if no file was submitted.
        filename: Original filename, or None if no file was submitted.
        content_type: MIME type reported by the upload, or None.

    Raises:
        NirWebIntakeValidationError: When validation fails.
    """
    if pdf_bytes is None or len(pdf_bytes) == 0:
        raise NirWebIntakeValidationError("No PDF file was submitted.")

    if not filename or not filename.strip():
        raise NirWebIntakeValidationError("Filename is required.")

    extension = _get_extension(filename)
    if extension not in _ACCEPTED_EXTENSIONS:
        raise NirWebIntakeValidationError(
            f"Invalid file type: '{extension}'. Only PDF files are accepted."
        )

    if content_type and content_type.strip().lower() not in _ACCEPTED_MIME_TYPES:
        raise NirWebIntakeValidationError(
            f"Invalid content type: '{content_type}'. Only PDF files are accepted."
        )

    # Basic PDF magic bytes check (first 5 bytes: %PDF-).
    if not pdf_bytes.startswith(b"%PDF-"):
        raise NirWebIntakeValidationError(
            "File content is not a valid PDF."
        )


def _get_extension(filename: str) -> str:
    """Extract and normalize the file extension from a filename."""
    import os

    _, ext = os.path.splitext(filename)
    return ext.lower()


class NirWebIntakeService:
    """Create case, store PDF, audit, and enqueue processing for NIR web uploads."""

    def __init__(
        self,
        *,
        case_repository: CaseRepositoryPort,
        audit_repository: AuditRepositoryPort,
        job_queue: JobQueuePort,
        pdf_storage: PdfFileStoragePort,
    ) -> None:
        self._case_repository = case_repository
        self._audit_repository = audit_repository
        self._job_queue = job_queue
        self._pdf_storage = pdf_storage

    async def ingest_web_pdf(
        self,
        *,
        pdf_bytes: bytes,
        filename: str,
        content_type: str | None,
        uploaded_by_user_id: str,
        uploaded_by_email: str,
    ) -> NirWebIntakeResult:
        """Validate, persist, and create case from NIR web PDF upload.

        Args:
            pdf_bytes: Raw PDF file content.
            filename: Original filename from the upload form.
            content_type: MIME type reported by the browser (may be None).
            uploaded_by_user_id: Authenticated user ID performing the upload.
            uploaded_by_email: Email of the authenticated user.

        Returns:
            A ``NirWebIntakeResult`` indicating success or failure.

        Raises:
            NirWebIntakeValidationError: When the uploaded file fails validation.
        """
        _validate_pdf_upload(
            pdf_bytes=pdf_bytes,
            filename=filename,
            content_type=content_type,
        )

        case_id = uuid4()
        logger.info(
            "nir_web_intake_received case_id=%s filename=%s uploaded_by=%s",
            case_id,
            filename,
            uploaded_by_email,
        )

        # 1. Store PDF to persistent storage
        storage_result = self._pdf_storage.save_pdf(
            case_id=case_id,
            pdf_bytes=pdf_bytes,
            filename=filename,
        )
        logger.info(
            "nir_web_intake_pdf_stored case_id=%s storage_path=%s",
            case_id,
            storage_result.storage_path,
        )

        # 2. Create case record
        created_case = await self._case_repository.create_web_case(
            WebCaseCreateInput(
                case_id=case_id,
                status=CaseStatus.R1_ACK_PROCESSING,
                origin_source="web",
                web_pdf_filename=filename,
                web_pdf_storage_path=storage_result.storage_path,
                web_uploaded_by_user_id=uploaded_by_user_id,
            )
        )
        logger.info(
            "nir_web_intake_case_created case_id=%s status=%s origin_source=web",
            created_case.case_id,
            created_case.status.value,
        )

        # 3. Persist auditable web event
        web_event = WebHumanEvent(
            case_id=case_id,
            origin=WebEventOrigin.WEB,
            actor=uploaded_by_email,
            timestamp=_now_utc(),
            event_type=WebEventType.NIR_PDF_UPLOAD,
            summary_text=f"PDF '{filename}' uploaded via web by {uploaded_by_email}",
        )

        await self._audit_repository.append_event(
            AuditEventCreateInput(
                case_id=case_id,
                actor_type="web_human",
                event_type=web_event.event_type.value,
                actor_user_id=uploaded_by_user_id,
                payload={
                    "origin": web_event.origin.value,
                    "actor": web_event.actor,
                    "summary_text": web_event.summary_text,
                    "event_type": web_event.event_type.value,
                    "filename": filename,
                    "storage_path": storage_result.storage_path,
                },
            )
        )
        logger.info(
            "nir_web_intake_audit_appended case_id=%s event_type=%s actor=%s",
            case_id,
            web_event.event_type.value,
            uploaded_by_email,
        )

        # 4. Enqueue downstream processing job
        await self._job_queue.enqueue(
            JobEnqueueInput(
                case_id=created_case.case_id,
                job_type="process_pdf_case",
                payload={
                    "web_pdf_storage_path": storage_result.storage_path,
                    "filename": filename,
                    "origin_source": "web",
                    "uploaded_by_user_id": uploaded_by_user_id,
                },
            )
        )
        logger.info(
            "nir_web_intake_job_enqueued case_id=%s job_type=process_pdf_case",
            created_case.case_id,
        )

        return NirWebIntakeResult(
            processed=True,
            case_id=str(created_case.case_id),
        )


def _now_utc() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(tz=UTC)
