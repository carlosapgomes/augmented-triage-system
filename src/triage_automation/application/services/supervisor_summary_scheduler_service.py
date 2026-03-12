"""Scheduler service for Room-4 periodic summary job enqueuing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from triage_automation.application.ports.job_queue_port import (
    JobEnqueueInput,
    JobQueuePort,
)
from triage_automation.application.ports.supervisor_summary_dispatch_repository_port import (
    SupervisorSummaryDispatchRepositoryPort,
    SupervisorSummaryWindowKey,
)


@dataclass(frozen=True)
class SupervisorSummaryWindow:
    """Resolved summary reporting window in local timezone and UTC."""

    window_start_local: datetime
    window_end_local: datetime
    window_start_utc: datetime
    window_end_utc: datetime


@dataclass(frozen=True)
class SupervisorSummaryScheduleResult:
    """Result summary for one scheduler execution attempt."""

    claimed_dispatch: bool
    enqueued_job_id: int | None
    window: SupervisorSummaryWindow


class SupervisorSummarySchedulerService:
    """Compute Room-4 summary window and enqueue canonical summary jobs."""

    def __init__(
        self,
        *,
        job_queue: JobQueuePort,
        dispatch_repository: SupervisorSummaryDispatchRepositoryPort,
        room4_id: str,
        timezone_name: str,
        cutoff_hours: list[int],
    ) -> None:
        self._job_queue = job_queue
        self._dispatch_repository = dispatch_repository
        self._room4_id = room4_id
        self._timezone_name = timezone_name
        self._cutoff_hours = list(cutoff_hours)

    async def enqueue_previous_window_summary(
        self,
        *,
        run_at_utc: datetime | None = None,
    ) -> SupervisorSummaryScheduleResult:
        """Enqueue one `post_room4_summary` job for previous cutoff window if claimed."""

        reference_now_utc = run_at_utc or datetime.now(tz=UTC)
        window = resolve_previous_summary_window(
            run_at_utc=reference_now_utc,
            timezone_name=self._timezone_name,
            cutoff_hours=self._cutoff_hours,
        )
        claimed_dispatch = await self._dispatch_repository.claim_window(
            SupervisorSummaryWindowKey(
                room_id=self._room4_id,
                window_start=window.window_start_utc,
                window_end=window.window_end_utc,
            )
        )
        if not claimed_dispatch:
            return SupervisorSummaryScheduleResult(
                claimed_dispatch=False,
                enqueued_job_id=None,
                window=window,
            )

        payload = {
            "room_id": self._room4_id,
            "window_start": window.window_start_utc.isoformat(),
            "window_end": window.window_end_utc.isoformat(),
            "timezone": self._timezone_name,
        }
        job = await self._job_queue.enqueue(
            JobEnqueueInput(
                job_type="post_room4_summary",
                case_id=None,
                payload=payload,
            )
        )
        return SupervisorSummaryScheduleResult(
            claimed_dispatch=True,
            enqueued_job_id=job.job_id,
            window=window,
        )


def resolve_previous_summary_window(
    *,
    run_at_utc: datetime,
    timezone_name: str,
    cutoff_hours: list[int],
) -> SupervisorSummaryWindow:
    """Resolve the latest completed summary window using configured daily cutoffs."""

    if run_at_utc.tzinfo is None:
        raise ValueError("run_at_utc must be timezone-aware")
    if len(cutoff_hours) < 2:
        raise ValueError("cutoff_hours must contain at least two entries")

    normalized_cutoffs = sorted(cutoff_hours)
    if len(set(normalized_cutoffs)) != len(normalized_cutoffs):
        raise ValueError("cutoff_hours must not contain duplicates")

    timezone = ZoneInfo(timezone_name)
    run_at_local = run_at_utc.astimezone(timezone)

    candidates: list[datetime] = []
    for day_offset in (-2, -1, 0):
        day = (run_at_local + timedelta(days=day_offset)).date()
        for cutoff_hour in normalized_cutoffs:
            candidates.append(
                datetime(
                    day.year,
                    day.month,
                    day.day,
                    cutoff_hour,
                    0,
                    0,
                    tzinfo=timezone,
                )
            )

    eligible_end = [candidate for candidate in candidates if candidate <= run_at_local]
    if not eligible_end:
        raise ValueError("unable to resolve previous summary cutoff")

    window_end_local = max(eligible_end)
    eligible_start = [candidate for candidate in candidates if candidate < window_end_local]
    if not eligible_start:
        raise ValueError("unable to resolve previous summary window start")

    window_start_local = max(eligible_start)

    return SupervisorSummaryWindow(
        window_start_local=window_start_local,
        window_end_local=window_end_local,
        window_start_utc=window_start_local.astimezone(UTC),
        window_end_utc=window_end_local.astimezone(UTC),
    )
