"""Failure finalization for jobs that exceeded max retries."""

from __future__ import annotations

from triage_automation.application.ports.audit_repository_port import (
    AuditEventCreateInput,
    AuditRepositoryPort,
)
from triage_automation.application.ports.case_repository_port import CaseRepositoryPort
from triage_automation.application.ports.job_queue_port import (
    JobEnqueueInput,
    JobQueuePort,
    JobRecord,
)
from triage_automation.domain.case_status import CaseStatus


class JobFailureService:
    """Handle max-retry exhaustion by moving case to FAILED and enqueueing final failure reply."""

    def __init__(
        self,
        *,
        case_repository: CaseRepositoryPort,
        audit_repository: AuditRepositoryPort,
        job_queue: JobQueuePort,
    ) -> None:
        self._case_repository = case_repository
        self._audit_repository = audit_repository
        self._job_queue = job_queue

    async def handle_max_retries(self, *, job: JobRecord) -> None:
        """Finalize case failure and enqueue Room-1 failure final-reply job."""

        if job.case_id is None:
            return

        await self._case_repository.update_status(case_id=job.case_id, status=CaseStatus.FAILED)
        await self._audit_repository.append_event(
            AuditEventCreateInput(
                case_id=job.case_id,
                actor_type="system",
                event_type="CASE_FAILED_MAX_RETRIES",
                payload={
                    "job_type": job.job_type,
                    "attempts": job.attempts,
                    "last_error": job.last_error,
                },
            )
        )

        failure_payload = {
            "cause": _categorize_failure(job.last_error),
            "details": (job.last_error or "unknown error")[:300],
        }

        await self._job_queue.enqueue(
            JobEnqueueInput(
                case_id=job.case_id,
                job_type="post_room1_final_failure",
                payload=failure_payload,
            )
        )
        await self._audit_repository.append_event(
            AuditEventCreateInput(
                case_id=job.case_id,
                actor_type="system",
                event_type="JOB_ENQUEUED_POST_ROOM1_FAILURE",
                payload={"job_type": "post_room1_final_failure"},
            )
        )


def _categorize_failure(last_error: str | None) -> str:
    if not last_error:
        return "other"

    lowered = last_error.lower()
    for candidate in ("download", "extract", "record_extract", "llm1", "llm2"):
        if candidate in lowered:
            return candidate
    return "other"
