"""worker entrypoint."""

from __future__ import annotations

import asyncio

from triage_automation.application.services.recovery_service import RecoveryService
from triage_automation.application.services.worker_runtime import WorkerRuntime
from triage_automation.config.settings import load_settings
from triage_automation.infrastructure.db.audit_repository import SqlAlchemyAuditRepository
from triage_automation.infrastructure.db.case_repository import SqlAlchemyCaseRepository
from triage_automation.infrastructure.db.job_queue_repository import SqlAlchemyJobQueueRepository
from triage_automation.infrastructure.db.session import create_session_factory
from triage_automation.infrastructure.db.worker_bootstrap import reconcile_running_jobs


async def _run_worker() -> None:
    settings = load_settings()

    session_factory = create_session_factory(settings.database_url)
    await reconcile_running_jobs(session_factory)

    queue = SqlAlchemyJobQueueRepository(session_factory)
    await RecoveryService(
        case_repository=SqlAlchemyCaseRepository(session_factory),
        audit_repository=SqlAlchemyAuditRepository(session_factory),
        job_queue=queue,
    ).recover()

    runtime = WorkerRuntime(queue=queue, handlers={})
    stop_event = asyncio.Event()

    await runtime.run_until_stopped(stop_event)


def main() -> None:
    """Run worker startup reconciliation and polling runtime."""

    asyncio.run(_run_worker())


if __name__ == "__main__":
    main()
