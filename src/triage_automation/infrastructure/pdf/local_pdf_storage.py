"""Local filesystem PDF storage adapter.

Persists uploaded PDF files to a configurable local directory,
organized by case ID for deterministic retrieval.
"""

from __future__ import annotations

import logging
from pathlib import Path

from triage_automation.application.ports.pdf_storage_port import (
    PdfStorageResult,
)

logger = logging.getLogger(__name__)


class LocalPdfFileStorage:
    """Store uploaded PDF files on the local filesystem.

    Files are saved under ``base_dir/<case_id>/<filename>``.
    The directory structure is created automatically.

    Args:
        base_dir: Root directory for PDF file storage.
    """

    def __init__(self, *, base_dir: Path) -> None:
        self._base_dir = base_dir

    def save_pdf(
        self,
        *,
        case_id: object,
        pdf_bytes: bytes,
        filename: str,
    ) -> PdfStorageResult:
        """Persist a PDF file to the local filesystem.

        Args:
            case_id: The case UUID this PDF belongs to.
            pdf_bytes: Raw PDF file content.
            filename: Original filename from the upload.

        Returns:
            A ``PdfStorageResult`` with the absolute storage path.

        Raises:
            OSError: If the file cannot be written.
        """
        from uuid import UUID

        resolved_case_id = UUID(str(case_id))
        case_dir = self._base_dir / str(resolved_case_id)
        case_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize filename to prevent path traversal.
        safe_filename = Path(filename).name
        target_path = case_dir / safe_filename

        target_path.write_bytes(pdf_bytes)

        logger.info(
            "pdf_file_stored case_id=%s path=%s bytes=%d",
            resolved_case_id,
            target_path,
            len(pdf_bytes),
        )

        return PdfStorageResult(
            storage_path=str(target_path),
            filename=safe_filename,
        )
