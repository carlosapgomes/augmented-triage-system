from __future__ import annotations

import importlib
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from triage_automation.application.ports.job_queue_port import JobRecord


def _resolve_previous_summary_window(*, run_at_utc: datetime) -> Any:
    module = importlib.import_module(
        "triage_automation.application.services.supervisor_summary_scheduler_service"
    )
    resolver = getattr(module, "resolve_previous_summary_window")
    return resolver(
        run_at_utc=run_at_utc,
        timezone_name="America/Bahia",
        morning_hour=7,
        evening_hour=19,
    )


def test_morning_cutoff_resolves_previous_night_window_in_utc() -> None:
    run_at_utc = datetime(2026, 2, 16, 10, 0, tzinfo=UTC)

    resolved = _resolve_previous_summary_window(run_at_utc=run_at_utc)

    assert resolved.window_start_utc == datetime(2026, 2, 15, 22, 0, tzinfo=UTC)
    assert resolved.window_end_utc == datetime(2026, 2, 16, 10, 0, tzinfo=UTC)
    assert resolved.window_start_utc < resolved.window_end_utc
    assert resolved.window_end_utc - resolved.window_start_utc == timedelta(hours=12)


def test_evening_cutoff_resolves_same_day_window_in_utc() -> None:
    run_at_utc = datetime(2026, 2, 16, 22, 0, tzinfo=UTC)

    resolved = _resolve_previous_summary_window(run_at_utc=run_at_utc)

    assert resolved.window_start_utc == datetime(2026, 2, 16, 10, 0, tzinfo=UTC)
    assert resolved.window_end_utc == datetime(2026, 2, 16, 22, 0, tzinfo=UTC)
    assert resolved.window_start_utc < resolved.window_end_utc
    assert resolved.window_end_utc - resolved.window_start_utc == timedelta(hours=12)


class _QueueSpy:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def enqueue(self, payload: Any) -> JobRecord:
        self.calls.append(
            {
                "job_type": payload.job_type,
                "case_id": payload.case_id,
                "payload": payload.payload,
            }
        )
        now = datetime.now(tz=UTC)
        return JobRecord(
            job_id=1,
            case_id=None,
            job_type=payload.job_type,
            status="queued",
            run_after=now,
            attempts=0,
            max_attempts=5,
            last_error=None,
            payload=payload.payload,
            created_at=now,
            updated_at=now,
        )


class _DispatchSpy:
    def __init__(self) -> None:
        self.claimed_keys: set[tuple[str, datetime, datetime]] = set()

    async def claim_window(self, payload: Any) -> bool:
        key = (payload.room_id, payload.window_start, payload.window_end)
        if key in self.claimed_keys:
            return False
        self.claimed_keys.add(key)
        return True


@pytest.mark.asyncio
async def test_scheduler_service_enqueues_post_room4_summary_with_canonical_utc_payload() -> None:
    module = importlib.import_module(
        "triage_automation.application.services.supervisor_summary_scheduler_service"
    )
    service_class = getattr(module, "SupervisorSummarySchedulerService")

    queue = _QueueSpy()
    dispatches = _DispatchSpy()
    service = service_class(
        job_queue=queue,
        dispatch_repository=dispatches,
        room4_id="!room4:example.org",
        timezone_name="America/Bahia",
        morning_hour=7,
        evening_hour=19,
    )

    result = await service.enqueue_previous_window_summary(
        run_at_utc=datetime(2026, 2, 16, 22, 0, tzinfo=UTC)
    )

    assert len(queue.calls) == 1
    call = queue.calls[0]
    assert call["job_type"] == "post_room4_summary"
    assert call["case_id"] is None
    assert call["payload"] == {
        "room_id": "!room4:example.org",
        "window_start": "2026-02-16T10:00:00+00:00",
        "window_end": "2026-02-16T22:00:00+00:00",
        "timezone": "America/Bahia",
    }
    assert result.claimed_dispatch is True
    assert result.enqueued_job_id == 1


@pytest.mark.asyncio
async def test_scheduler_service_skips_duplicate_window_for_manual_rerun() -> None:
    module = importlib.import_module(
        "triage_automation.application.services.supervisor_summary_scheduler_service"
    )
    service_class = getattr(module, "SupervisorSummarySchedulerService")

    queue = _QueueSpy()
    dispatches = _DispatchSpy()
    service = service_class(
        job_queue=queue,
        dispatch_repository=dispatches,
        room4_id="!room4:example.org",
        timezone_name="America/Bahia",
        morning_hour=7,
        evening_hour=19,
    )

    first = await service.enqueue_previous_window_summary(
        run_at_utc=datetime(2026, 2, 16, 22, 0, tzinfo=UTC)
    )
    second = await service.enqueue_previous_window_summary(
        run_at_utc=datetime(2026, 2, 16, 22, 0, tzinfo=UTC)
    )

    assert len(queue.calls) == 1
    assert first.claimed_dispatch is True
    assert first.enqueued_job_id == 1
    assert second.claimed_dispatch is False
    assert second.enqueued_job_id is None
