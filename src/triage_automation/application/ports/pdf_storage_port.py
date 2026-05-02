"""Port for PDF file storage operations.

Provides an abstraction for persisting uploaded PDF files,
allowing the application layer to remain agnostic of the
concrete storage mechanism (local filesystem, object store, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class PdfStorageResult:
    """Outcome of a PDF file storage operation.

    Attributes:
        storage_path: The path or identifier where the file was stored.
        filename: The original filename of the stored PDF.
    """

    storage_path: str
    filename: str


class PdfFileStoragePort(Protocol):
    """Protocol for persisting uploaded PDF files."""

    def save_pdf(
        self,
        *,
        case_id: UUID,
        pdf_bytes: bytes,
        filename: str,
    ) -> PdfStorageResult:
        """Persist a PDF file and return its storage location.

        Args:
            case_id: The case this PDF belongs to.
            pdf_bytes: Raw PDF file content.
            filename: Original filename from the upload.

        Returns:
            A ``PdfStorageResult`` with the storage path and filename.
        """
