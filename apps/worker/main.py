"""worker entrypoint."""

from __future__ import annotations

import asyncio

from triage_automation.application.ports.job_queue_port import JobRecord
from triage_automation.application.services.recovery_service import RecoveryService
from triage_automation.application.services.worker_runtime import JobHandler, WorkerRuntime
from triage_automation.config.settings import load_settings
from triage_automation.infrastructure.db.audit_repository import SqlAlchemyAuditRepository
from triage_automation.infrastructure.db.case_repository import SqlAlchemyCaseRepository
from triage_automation.infrastructure.db.job_queue_repository import SqlAlchemyJobQueueRepository
from triage_automation.infrastructure.db.session import create_session_factory
from triage_automation.infrastructure.db.worker_bootstrap import reconcile_running_jobs


def build_worker_handlers(
    *,
    process_pdf_case_handler: JobHandler,
    post_room2_widget_handler: JobHandler,
    post_room3_request_handler: JobHandler,
    post_room1_final_handler: JobHandler,
    execute_cleanup_handler: JobHandler,
) -> dict[str, JobHandler]:
    """Build explicit runtime handler map for all supported production job types."""

    return {
        "process_pdf_case": process_pdf_case_handler,
        "post_room2_widget": post_room2_widget_handler,
        "post_room3_request": post_room3_request_handler,
        "post_room1_final_denial_triage": post_room1_final_handler,
        "post_room1_final_appt": post_room1_final_handler,
        "post_room1_final_appt_denied": post_room1_final_handler,
        "post_room1_final_failure": post_room1_final_handler,
        "execute_cleanup": execute_cleanup_handler,
    }


async def _unwired_runtime_handler(_: JobRecord) -> None:
    """Placeholder handler until service wiring is added in the next slice."""

    raise NotImplementedError("runtime service wiring is implemented in a later slice")


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

    handlers = build_worker_handlers(
        process_pdf_case_handler=_unwired_runtime_handler,
        post_room2_widget_handler=_unwired_runtime_handler,
        post_room3_request_handler=_unwired_runtime_handler,
        post_room1_final_handler=_unwired_runtime_handler,
        execute_cleanup_handler=_unwired_runtime_handler,
    )

    runtime = WorkerRuntime(queue=queue, handlers=handlers)
    stop_event = asyncio.Event()

    await runtime.run_until_stopped(stop_event)


def main() -> None:
    """Run worker startup reconciliation and polling runtime."""

    asyncio.run(_run_worker())


if __name__ == "__main__":
    main()
