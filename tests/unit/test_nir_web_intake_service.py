"""Unit tests for NirWebIntakeService.

TDD tests for slice 2.1 — validates that:
- Valid PDF upload creates a case.
- Upload without a file is rejected.
- Upload of non-PDF file is rejected.
- The NIR user action is auditable (audit event carries web origin).
- The downstream processing job is dispatched.
- The case status reflects a processing-acknowledged state.
- Invalid PDF magic bytes are rejected.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from triage_automation.application.ports.audit_repository_port import AuditEventCreateInput
from triage_automation.application.ports.case_repository_port import (
    CaseRecord,
    WebCaseCreateInput,
)
from triage_automation.application.ports.job_queue_port import JobEnqueueInput, JobRecord
from triage_automation.application.ports.pdf_storage_port import PdfStorageResult
from triage_automation.application.services.nir_web_intake_service import (
    NirWebIntakeService,
    NirWebIntakeValidationError,
)
from triage_automation.domain.case_status import CaseStatus

# ── Fakes / Stubs ──────────────────────────────────────────────────────


class FakePdfStorage:
    """In-memory fake for PdfFileStoragePort."""

    def __init__(self) -> None:
        self.saved: dict[UUID, tuple[bytes, str]] = {}

    def save_pdf(
        self,
        *,
        case_id: UUID,
        pdf_bytes: bytes,
        filename: str,
    ) -> PdfStorageResult:
        self.saved[case_id] = (pdf_bytes, filename)
        return PdfStorageResult(
            storage_path=f"/tmp/ats_pdfs/{case_id}/{filename}",
            filename=filename,
        )


class FakeCaseRepository:
    """In-memory fake for CaseRepositoryPort (web-case subset)."""

    def __init__(self) -> None:
        self.cases: dict[UUID, CaseRecord] = {}

    async def create_web_case(self, payload: WebCaseCreateInput) -> CaseRecord:
        now = datetime.now(tz=UTC)
        record = CaseRecord(
            case_id=payload.case_id,
            status=payload.status,
            origin_source=payload.origin_source,
            room1_origin_room_id=None,
            room1_origin_event_id=None,
            room1_sender_user_id=None,
            web_pdf_storage_path=payload.web_pdf_storage_path,
            created_at=now,
            updated_at=now,
        )
        self.cases[payload.case_id] = record
        return record


class FakeAuditRepository:
    """In-memory fake for AuditRepositoryPort."""

    def __init__(self) -> None:
        self.events: list[AuditEventCreateInput] = []

    async def append_event(self, payload: AuditEventCreateInput) -> int:
        self.events.append(payload)
        return len(self.events)


class FakeJobQueue:
    """In-memory fake for JobQueuePort."""

    def __init__(self) -> None:
        self.jobs: list[JobEnqueueInput] = []

    async def enqueue(self, payload: JobEnqueueInput) -> JobRecord:
        self.jobs.append(payload)
        return JobRecord(
            job_id=len(self.jobs),
            case_id=payload.case_id,
            job_type=payload.job_type,
            status="queued",
            run_after=datetime.now(tz=UTC),
            attempts=0,
            max_attempts=5,
            last_error=None,
            payload=payload.payload,
            created_at=datetime.now(tz=UTC),
            updated_at=datetime.now(tz=UTC),
        )


FakeServices = tuple[
    NirWebIntakeService, FakeCaseRepository, FakeAuditRepository, FakeJobQueue, FakePdfStorage
]


def _make_service() -> FakeServices:
    """Create a NirWebIntakeService with all fakes injected."""
    case_repo = FakeCaseRepository()
    audit_repo = FakeAuditRepository()
    job_queue = FakeJobQueue()
    pdf_storage = FakePdfStorage()
    service = NirWebIntakeService(
        case_repository=case_repo,
        audit_repository=audit_repo,
        job_queue=job_queue,
        pdf_storage=pdf_storage,
    )
    return service, case_repo, audit_repo, job_queue, pdf_storage


def _valid_pdf_bytes() -> bytes:
    """Return minimal valid PDF bytes for testing."""
    return b"%PDF-1.4\n%fake pdf content for testing"


# ── Valid upload tests ─────────────────────────────────────────────────


class TestNirWebIntakeValidUpload:
    """Valid PDF upload creates a case, stores PDF, audits, and enqueues job."""

    @pytest.mark.asyncio
    async def test_valid_pdf_creates_case(self) -> None:
        service, case_repo, _, _, _ = _make_service()
        result = await service.ingest_web_pdf(
            pdf_bytes=_valid_pdf_bytes(),
            filename="referral.pdf",
            content_type="application/pdf",
            uploaded_by_user_id="user-123",
            uploaded_by_email="nir@example.com",
        )
        assert result.processed is True
        assert result.case_id is not None
        case_id = UUID(result.case_id)
        assert case_id in case_repo.cases
        case = case_repo.cases[case_id]
        assert case.status == CaseStatus.R1_ACK_PROCESSING
        assert case.origin_source == "web"

    @pytest.mark.asyncio
    async def test_valid_pdf_stores_file(self) -> None:
        service, _, _, _, pdf_storage = _make_service()
        result = await service.ingest_web_pdf(
            pdf_bytes=_valid_pdf_bytes(),
            filename="referral.pdf",
            content_type="application/pdf",
            uploaded_by_user_id="user-123",
            uploaded_by_email="nir@example.com",
        )
        assert result.case_id is not None
        case_id = UUID(result.case_id)
        assert case_id in pdf_storage.saved
        stored_bytes, stored_name = pdf_storage.saved[case_id]
        assert stored_bytes == _valid_pdf_bytes()
        assert stored_name == "referral.pdf"

    @pytest.mark.asyncio
    async def test_valid_pdf_appends_audit_event(self) -> None:
        service, _, audit_repo, _, _ = _make_service()
        result = await service.ingest_web_pdf(
            pdf_bytes=_valid_pdf_bytes(),
            filename="referral.pdf",
            content_type="application/pdf",
            uploaded_by_user_id="user-123",
            uploaded_by_email="nir@example.com",
        )
        assert result.processed is True
        assert len(audit_repo.events) == 1
        event = audit_repo.events[0]
        assert event.actor_type == "web_human"
        assert event.actor_user_id == "user-123"
        assert event.payload.get("origin") == "web"
        assert event.payload.get("actor") == "nir@example.com"
        assert event.payload.get("event_type") == "NIR_PDF_UPLOAD"
        assert event.payload.get("filename") == "referral.pdf"

    @pytest.mark.asyncio
    async def test_valid_pdf_enqueues_processing_job(self) -> None:
        service, _, _, job_queue, _ = _make_service()
        result = await service.ingest_web_pdf(
            pdf_bytes=_valid_pdf_bytes(),
            filename="referral.pdf",
            content_type="application/pdf",
            uploaded_by_user_id="user-123",
            uploaded_by_email="nir@example.com",
        )
        assert result.processed is True
        assert len(job_queue.jobs) == 1
        job = job_queue.jobs[0]
        assert job.job_type == "process_pdf_case"
        assert job.payload.get("origin_source") == "web"
        assert job.payload.get("filename") == "referral.pdf"
        assert job.payload.get("web_pdf_storage_path") is not None

    @pytest.mark.asyncio
    async def test_action_attributed_to_authenticated_user(self) -> None:
        service, _, audit_repo, _, _ = _make_service()
        result = await service.ingest_web_pdf(
            pdf_bytes=_valid_pdf_bytes(),
            filename="referral.pdf",
            content_type="application/pdf",
            uploaded_by_user_id="user-456",
            uploaded_by_email="nir.operator@hospital.org",
        )
        assert result.processed is True
        event = audit_repo.events[0]
        assert event.actor_user_id == "user-456"
        assert event.payload.get("actor") == "nir.operator@hospital.org"


# ── Validation rejection tests ─────────────────────────────────────────


class TestNirWebIntakeValidation:
    """Invalid uploads are rejected deterministically."""

    @pytest.mark.asyncio
    async def test_upload_without_file_rejected(self) -> None:
        service = _make_service()[0]
        with pytest.raises(NirWebIntakeValidationError, match="No PDF file"):
            await service.ingest_web_pdf(
                pdf_bytes=b"",
                filename="",
                content_type=None,
                uploaded_by_user_id="user-123",
                uploaded_by_email="nir@example.com",
            )

    @pytest.mark.asyncio
    async def test_upload_non_pdf_extension_rejected(self) -> None:
        service = _make_service()[0]
        with pytest.raises(NirWebIntakeValidationError, match="Invalid file type"):
            await service.ingest_web_pdf(
                pdf_bytes=b"%PDF-1.4 some content",
                filename="document.docx",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                uploaded_by_user_id="user-123",
                uploaded_by_email="nir@example.com",
            )

    @pytest.mark.asyncio
    async def test_upload_non_pdf_content_type_rejected(self) -> None:
        service = _make_service()[0]
        with pytest.raises(NirWebIntakeValidationError, match="Invalid content type"):
            await service.ingest_web_pdf(
                pdf_bytes=b"%PDF-1.4 some content",
                filename="document.pdf",
                content_type="image/jpeg",
                uploaded_by_user_id="user-123",
                uploaded_by_email="nir@example.com",
            )

    @pytest.mark.asyncio
    async def test_upload_invalid_pdf_magic_bytes_rejected(self) -> None:
        service = _make_service()[0]
        with pytest.raises(NirWebIntakeValidationError, match="not a valid PDF"):
            await service.ingest_web_pdf(
                pdf_bytes=b"This is not a PDF at all",
                filename="document.pdf",
                content_type="application/pdf",
                uploaded_by_user_id="user-123",
                uploaded_by_email="nir@example.com",
            )

    @pytest.mark.asyncio
    async def test_upload_none_bytes_rejected(self) -> None:
        service = _make_service()[0]
        with pytest.raises(NirWebIntakeValidationError, match="No PDF file"):
            await service.ingest_web_pdf(
                pdf_bytes=None,  # type: ignore[arg-type]
                filename="document.pdf",
                content_type="application/pdf",
                uploaded_by_user_id="user-123",
                uploaded_by_email="nir@example.com",
            )
