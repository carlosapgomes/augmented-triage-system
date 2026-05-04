"""Service wiring for Django views that need access to shared application services.

Creates async SQLAlchemy-backed services for use by Django views.
Django views call async services via ``asyncio.run()`` bridge.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from django.conf import settings

from apps.django_ops.django_prompt_store_adapter import (
    DjangoOrmPromptStoreAdapter,
)
from triage_automation.application.ports.audit_repository_port import AuditRepositoryPort
from triage_automation.application.ports.case_repository_port import CaseRepositoryPort
from triage_automation.application.ports.job_queue_port import JobQueuePort
from triage_automation.application.ports.pdf_storage_port import PdfFileStoragePort
from triage_automation.application.services.django_prompt_management import (
    DjangoPromptManagementService,
)
from triage_automation.application.services.django_user_management import (
    DjangoUserManagementService,
)
from triage_automation.application.services.doctor_queue_service import DoctorQueueService
from triage_automation.application.services.handle_doctor_decision_service import (
    HandleDoctorDecisionService,
)
from triage_automation.application.services.handle_scheduler_confirmation_service import (
    HandleSchedulerConfirmationService,
)
from triage_automation.application.services.manager_dashboard_service import (
    ManagerDashboardService,
)
from triage_automation.application.services.nir_dashboard_service import NirDashboardService
from triage_automation.application.services.nir_final_acknowledgment_service import (
    NirFinalAcknowledgmentService,
)
from triage_automation.application.services.nir_web_intake_service import NirWebIntakeService
from triage_automation.application.services.scheduler_queue_service import SchedulerQueueService
from triage_automation.infrastructure.db.audit_repository import SqlAlchemyAuditRepository
from triage_automation.infrastructure.db.auth_event_repository import SqlAlchemyAuthEventRepository
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


def build_scheduler_queue_service() -> SchedulerQueueService:
    """Build the SchedulerQueueService with all dependencies wired.

    Returns:
        A fully configured ``SchedulerQueueService`` ready for use.
    """
    database_url = _get_database_url()
    session_factory = create_session_factory(database_url)

    case_repository: CaseRepositoryPort = SqlAlchemyCaseRepository(session_factory)

    return SchedulerQueueService(
        case_repository=case_repository,
    )


def build_handle_doctor_decision_service() -> HandleDoctorDecisionService:
    """Build the HandleDoctorDecisionService without Matrix dependencies.

    For the web workflow, Matrix Room-2 posting is omitted. The service
    focuses purely on the core decision logic: state check, CAS update,
    audit persistence, and next-step job enqueue.

    Returns:
        A fully configured ``HandleDoctorDecisionService`` ready for use.
    """
    database_url = _get_database_url()
    session_factory = create_session_factory(database_url)

    case_repository: CaseRepositoryPort = SqlAlchemyCaseRepository(session_factory)
    audit_repository: AuditRepositoryPort = SqlAlchemyAuditRepository(session_factory)
    job_queue: JobQueuePort = SqlAlchemyJobQueueRepository(session_factory)

    return HandleDoctorDecisionService(
        case_repository=case_repository,
        audit_repository=audit_repository,
        job_queue=job_queue,
        # No Matrix poster, message repository, room2_id, or
        # reaction checkpoint repository — web-only path.
    )


def build_handle_scheduler_confirmation_service() -> HandleSchedulerConfirmationService:
    """Build the HandleSchedulerConfirmationService without Matrix dependencies.

    For the web workflow, Matrix Room-3 reply posting is omitted. The service
    focuses purely on the core confirmation logic: state check, CAS update,
    audit persistence, and next-step job enqueue.

    Returns:
        A fully configured ``HandleSchedulerConfirmationService`` ready for use.
    """
    database_url = _get_database_url()
    session_factory = create_session_factory(database_url)

    case_repository: CaseRepositoryPort = SqlAlchemyCaseRepository(session_factory)
    audit_repository: AuditRepositoryPort = SqlAlchemyAuditRepository(session_factory)
    job_queue: JobQueuePort = SqlAlchemyJobQueueRepository(session_factory)

    return HandleSchedulerConfirmationService(
        case_repository=case_repository,
        audit_repository=audit_repository,
        job_queue=job_queue,
        # No Matrix poster, message repository, reaction checkpoint
        # repository, or room3_id — web-only path.
    )


def build_manager_dashboard_service() -> ManagerDashboardService:
    """Build the ManagerDashboardService with all dependencies wired.

    Returns:
        A fully configured ``ManagerDashboardService`` ready for use.
    """
    database_url = _get_database_url()
    session_factory = create_session_factory(database_url)

    case_repository: CaseRepositoryPort = SqlAlchemyCaseRepository(session_factory)

    return ManagerDashboardService(
        case_repository=case_repository,
    )


def build_nir_final_acknowledgment_service() -> NirFinalAcknowledgmentService:
    """Build the NirFinalAcknowledgmentService with all dependencies wired.

    Uses the same CAS path (``claim_cleanup_trigger_if_first``) as
    ``ReactionService``, ensuring identical idempotent closure semantics
    between the web and Matrix cleanup trigger paths.

    Returns:
        A fully configured ``NirFinalAcknowledgmentService`` ready for use.
    """
    database_url = _get_database_url()
    session_factory = create_session_factory(database_url)

    case_repository: CaseRepositoryPort = SqlAlchemyCaseRepository(session_factory)
    audit_repository: AuditRepositoryPort = SqlAlchemyAuditRepository(session_factory)
    job_queue: JobQueuePort = SqlAlchemyJobQueueRepository(session_factory)

    return NirFinalAcknowledgmentService(
        case_repository=case_repository,
        audit_repository=audit_repository,
        job_queue=job_queue,
    )


def build_django_user_management_service() -> DjangoUserManagementService:
    """Build the DjangoUserManagementService with all dependencies wired.

    Returns:
        A fully configured ``DjangoUserManagementService`` ready for use.
    """
    database_url = _get_database_url()
    session_factory = create_session_factory(database_url)

    from apps.django_ops.django_user_store_adapter import DjangoOrmUserStoreAdapter

    store = DjangoOrmUserStoreAdapter()
    auth_event_repo = SqlAlchemyAuthEventRepository(session_factory)

    return DjangoUserManagementService(
        store=store,
        auth_events=auth_event_repo,
    )


def build_django_prompt_management_service() -> DjangoPromptManagementService:
    """Build the DjangoPromptManagementService with all dependencies wired.

    Returns:
        A fully configured ``DjangoPromptManagementService`` ready for use.
    """
    from triage_automation.infrastructure.db.prompt_template_repository import (
        SqlAlchemyPromptTemplateRepository,
    )

    database_url = _get_database_url()
    session_factory = create_session_factory(database_url)

    prompt_management = SqlAlchemyPromptTemplateRepository(session_factory)
    store = DjangoOrmPromptStoreAdapter(
        prompt_management=prompt_management,
        session_factory=session_factory,
    )
    auth_event_repo = SqlAlchemyAuthEventRepository(session_factory)

    return DjangoPromptManagementService(
        store=store,
        auth_events=auth_event_repo,
    )


def run_async(coro: object) -> object:
    """Run an async coroutine from synchronous Django view context.

    Args:
        coro: The coroutine to execute.

    Returns:
        The result of the coroutine.
    """
    return asyncio.run(coro)  # type: ignore[arg-type]
