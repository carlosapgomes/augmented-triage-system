"""Scheduler entrypoint for one-shot Room-4 summary job enqueuing."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from triage_automation.application.services.supervisor_summary_scheduler_service import (
    SupervisorSummaryScheduleResult,
    SupervisorSummarySchedulerService,
)
from triage_automation.config.settings import Settings, load_settings
from triage_automation.infrastructure.db.job_queue_repository import SqlAlchemyJobQueueRepository
from triage_automation.infrastructure.db.session import create_session_factory
from triage_automation.infrastructure.db.supervisor_summary_dispatch_repository import (
    SqlAlchemySupervisorSummaryDispatchRepository,
)
from triage_automation.infrastructure.logging import configure_logging

logger = logging.getLogger(__name__)


def build_scheduler_service(
    *,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> SupervisorSummarySchedulerService:
    """Build scheduler service and SQLAlchemy-backed dependencies."""

    runtime_session_factory = session_factory or create_session_factory(settings.database_url)
    return SupervisorSummarySchedulerService(
        job_queue=SqlAlchemyJobQueueRepository(runtime_session_factory),
        dispatch_repository=SqlAlchemySupervisorSummaryDispatchRepository(
            runtime_session_factory
        ),
        room4_id=settings.room4_id,
        timezone_name=settings.supervisor_summary_timezone,
        morning_hour=settings.supervisor_summary_morning_hour,
        evening_hour=settings.supervisor_summary_evening_hour,
    )


async def run_scheduler_once(
    *,
    settings: Settings | None = None,
    scheduler_service: SupervisorSummarySchedulerService | None = None,
    run_at_utc: datetime | None = None,
) -> SupervisorSummaryScheduleResult:
    """Execute one scheduler pass and return enqueue/idempotency result."""

    runtime_settings = settings or load_settings()
    configure_logging(level=runtime_settings.log_level)
    runtime_scheduler_service = scheduler_service or build_scheduler_service(
        settings=runtime_settings
    )
    reference_now_utc = run_at_utc or datetime.now(tz=UTC)
    result = await runtime_scheduler_service.enqueue_previous_window_summary(
        run_at_utc=reference_now_utc
    )
    logger.info(
        (
            "scheduler_room4_summary_run claimed_dispatch=%s enqueued_job_id=%s "
            "room4_id=%s window_start_utc=%s window_end_utc=%s"
        ),
        result.claimed_dispatch,
        result.enqueued_job_id,
        runtime_settings.room4_id,
        result.window.window_start_utc.isoformat(),
        result.window.window_end_utc.isoformat(),
    )
    return result


async def _run_scheduler_once() -> None:
    """Run one scheduler pass with runtime settings and infrastructure wiring."""

    await run_scheduler_once()


def main() -> None:
    """Run one-shot scheduler runtime for Room-4 summary enqueuing."""

    asyncio.run(_run_scheduler_once())


if __name__ == "__main__":
    main()
