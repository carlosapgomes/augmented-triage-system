"""Port definitions for Postgres-backed job queue operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID


@dataclass(frozen=True)
class JobEnqueueInput:
    """Input payload for inserting a job into the queue."""

    job_type: str
    case_id: UUID | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    run_after: datetime | None = None
    max_attempts: int = 5


@dataclass(frozen=True)
class JobRecord:
    """Persisted queue record used by worker/runtime logic."""

    job_id: int
    case_id: UUID | None
    job_type: str
    status: str
    run_after: datetime
    attempts: int
    max_attempts: int
    last_error: str | None
    payload: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class JobQueuePort(Protocol):
    """Async queue operations contract."""

    async def enqueue(self, payload: JobEnqueueInput) -> JobRecord:
        """Create a queued job."""

    async def claim_due_jobs(self, *, limit: int) -> list[JobRecord]:
        """Atomically claim due queued jobs and mark them running."""

    async def mark_done(self, *, job_id: int) -> None:
        """Mark a job as done."""

    async def mark_failed(self, *, job_id: int, last_error: str) -> None:
        """Mark a job as failed and persist latest error."""

    async def schedule_retry(
        self,
        *,
        job_id: int,
        run_after: datetime,
        last_error: str,
    ) -> JobRecord:
        """Increment attempts and requeue with a future run_after."""

    async def mark_dead(self, *, job_id: int, last_error: str) -> JobRecord:
        """Mark a job as dead after retries are exhausted."""

    async def has_active_job(self, *, case_id: UUID, job_type: str) -> bool:
        """Return whether a queued/running job exists for case and type."""
