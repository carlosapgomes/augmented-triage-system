"""Service wiring for Django views that need access to shared application services.

Creates async SQLAlchemy-backed services for use by Django views.
Django views call async services via ``asyncio.run()`` bridge.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from django.conf import settings

from triage_automation.application.ports.audit_repository_port import AuditRepositoryPort
from triage_automation.application.ports.case_repository_port import CaseRepositoryPort
from triage_automation.application.ports.job_queue_port import JobQueuePort
from triage_automation.application.ports.pdf_storage_port import PdfFileStoragePort
from triage_automation.application.services.doctor_queue_service import DoctorQueueService
from triage_automation.application.services.nir_dashboard_service import NirDashboardService
from triage_automation.application.services.nir_web_intake_service import NirWebIntakeService
from triage_automation.infrastructure.db.audit_repository import SqlAlchemyAuditRepository
from triage_automation.infrastructure.db.case_repository import SqlAlchemyCaseRepository
from triage_automation.infrastructure.db.job_queue_repository import SqlAlchemyJobQueueRepository
from triage_automation.infrastructure.db.session import create_session_factory
from triage_automation.infrastructure.pdf.local_pdf_storage import LocalPdfFileStorage


def _get_database_url() -> str:
    """Resolve the SQLAlchemy database URL from environment or settings."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        # Fallback: use Django's default database configuration.
        db_config = settings.DATABASES.get("default", {})
        db_name = db_config.get("NAME", "")
        if db_name:
            url = f"sqlite+aiosqlite:///{db_name}"
    return url


def _build_pdf_storage() -> PdfFileStoragePort:
    """Build the PDF file storage adapter."""
    storage_dir = Path(getattr(settings, "PDF_STORAGE_DIR", "/tmp/ats_pdfs"))
    return LocalPdfFileStorage(base_dir=storage_dir)


def build_nir_web_intake_service() -> NirWebIntakeService:
    """Build the NirWebIntakeService with all dependencies wired.

    Returns:
        A fully configured ``NirWebIntakeService`` ready for use.
    """
    database_url = _get_database_url()
    session_factory = create_session_factory(database_url)

    case_repository: CaseRepositoryPort = SqlAlchemyCaseRepository(session_factory)
    audit_repository: AuditRepositoryPort = SqlAlchemyAuditRepository(session_factory)
    job_queue: JobQueuePort = SqlAlchemyJobQueueRepository(session_factory)
    pdf_storage = _build_pdf_storage()

    return NirWebIntakeService(
        case_repository=case_repository,
        audit_repository=audit_repository,
        job_queue=job_queue,
        pdf_storage=pdf_storage,
    )


def build_nir_dashboard_service() -> NirDashboardService:
    """Build the NirDashboardService with all dependencies wired.

    Returns:
        A fully configured ``NirDashboardService`` ready for use.
    """
    database_url = _get_database_url()
    session_factory = create_session_factory(database_url)

    case_repository: CaseRepositoryPort = SqlAlchemyCaseRepository(session_factory)

    return NirDashboardService(
        case_repository=case_repository,
    )


def build_doctor_queue_service() -> DoctorQueueService:
    """Build the DoctorQueueService with all dependencies wired.

    Returns:
        A fully configured ``DoctorQueueService`` ready for use.
    """
    database_url = _get_database_url()
    session_factory = create_session_factory(database_url)

    case_repository: CaseRepositoryPort = SqlAlchemyCaseRepository(session_factory)

    return DoctorQueueService(
        case_repository=case_repository,
    )


def run_async(coro: object) -> object:
    """Run an async coroutine from synchronous Django view context.

    Args:
        coro: The coroutine to execute.

    Returns:
        The result of the coroutine.
    """
    return asyncio.run(coro)  # type: ignore[arg-type]
