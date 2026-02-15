from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from apps.worker.main import build_worker_handlers
from triage_automation.application.ports.job_queue_port import JobRecord
from triage_automation.application.services.worker_runtime import WorkerRuntime


class _QueueForUnknownType:
    def __init__(self, job: JobRecord) -> None:
        self._job: JobRecord | None = job
        self.schedule_retry_calls: list[tuple[int, str]] = []

    async def claim_due_jobs(self, *, limit: int) -> list[JobRecord]:
        _ = limit
        if self._job is None:
            return []
        job = self._job
        self._job = None
        return [job]

    async def enqueue(self, payload: object) -> JobRecord:  # pragma: no cover - not used here
        _ = payload
        raise NotImplementedError

    async def mark_done(self, *, job_id: int) -> None:  # pragma: no cover - not used here
        _ = job_id
        raise NotImplementedError

    async def mark_failed(
        self,
        *,
        job_id: int,
        last_error: str,
    ) -> None:  # pragma: no cover - not used here
        _ = job_id, last_error
        raise NotImplementedError

    async def schedule_retry(
        self,
        *,
        job_id: int,
        run_after: datetime,
        last_error: str,
    ) -> JobRecord:
        _ = run_after
        self.schedule_retry_calls.append((job_id, last_error))
        return _make_job(job_type="queued-retry", job_id=job_id)

    async def mark_dead(
        self,
        *,
        job_id: int,
        last_error: str,
    ) -> JobRecord:  # pragma: no cover - not used here
        _ = job_id, last_error
        raise NotImplementedError

    async def has_active_job(
        self,
        *,
        case_id: object,
        job_type: str,
    ) -> bool:  # pragma: no cover - not used here
        _ = case_id, job_type
        return False


def _make_job(*, job_type: str, job_id: int = 1) -> JobRecord:
    now = datetime.now(tz=UTC)
    return JobRecord(
        job_id=job_id,
        case_id=uuid4(),
        job_type=job_type,
        status="running",
        run_after=now,
        attempts=0,
        max_attempts=3,
        last_error=None,
        payload={},
        created_at=now,
        updated_at=now,
    )


async def _noop_handler(job: JobRecord) -> None:
    _ = job


def test_build_worker_handlers_contains_required_runtime_job_types() -> None:
    handlers = build_worker_handlers(
        process_pdf_case_handler=_noop_handler,
        post_room2_widget_handler=_noop_handler,
        post_room3_request_handler=_noop_handler,
        post_room1_final_handler=_noop_handler,
        execute_cleanup_handler=_noop_handler,
    )

    assert set(handlers) == {
        "process_pdf_case",
        "post_room2_widget",
        "post_room3_request",
        "post_room1_final_denial_triage",
        "post_room1_final_appt",
        "post_room1_final_appt_denied",
        "post_room1_final_failure",
        "execute_cleanup",
    }


@pytest.mark.asyncio
async def test_unknown_job_type_behavior_remains_unchanged() -> None:
    queue = _QueueForUnknownType(_make_job(job_type="unknown-type", job_id=42))
    handlers = build_worker_handlers(
        process_pdf_case_handler=_noop_handler,
        post_room2_widget_handler=_noop_handler,
        post_room3_request_handler=_noop_handler,
        post_room1_final_handler=_noop_handler,
        execute_cleanup_handler=_noop_handler,
    )
    runtime = WorkerRuntime(queue=queue, handlers=handlers)

    claimed_count = await runtime.run_once()

    assert claimed_count == 1
    assert queue.schedule_retry_calls == [
        (42, "Unknown job type: unknown-type"),
    ]
