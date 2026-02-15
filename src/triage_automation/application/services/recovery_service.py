"""Recovery scan service for restarting non-terminal cases safely."""

from __future__ import annotations

from dataclasses import dataclass

from triage_automation.application.ports.audit_repository_port import (
    AuditEventCreateInput,
    AuditRepositoryPort,
)
from triage_automation.application.ports.case_repository_port import (
    CaseRecoverySnapshot,
    CaseRepositoryPort,
)
from triage_automation.application.ports.job_queue_port import JobEnqueueInput, JobQueuePort
from triage_automation.domain.case_status import CaseStatus


@dataclass(frozen=True)
class RecoveryResult:
    """Summary for a single worker boot recovery scan."""

    scanned_cases: int
    enqueued_jobs: int


class RecoveryService:
    """Reconcile non-terminal cases by restoring missing queued work."""

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

    async def recover(self) -> RecoveryResult:
        """Scan non-terminal cases and enqueue missing continuation jobs."""

        snapshots = await self._case_repository.list_non_terminal_cases_for_recovery()
        enqueued = 0

        for snapshot in snapshots:
            recovery_job = _resolve_recovery_job(snapshot)
            if recovery_job is None:
                continue

            if await self._job_queue.has_active_job(
                case_id=snapshot.case_id,
                job_type=recovery_job,
            ):
                continue

            payload: dict[str, object] = {}
            if recovery_job == "post_room1_final_failure":
                payload = {
                    "cause": "other",
                    "details": "recovery enqueued missing failure finalization job",
                }

            await self._job_queue.enqueue(
                JobEnqueueInput(
                    case_id=snapshot.case_id,
                    job_type=recovery_job,
                    payload=payload,
                )
            )
            await self._audit_repository.append_event(
                AuditEventCreateInput(
                    case_id=snapshot.case_id,
                    actor_type="system",
                    event_type="RECOVERY_JOB_ENQUEUED",
                    payload={
                        "status": snapshot.status.value,
                        "job_type": recovery_job,
                    },
                )
            )
            enqueued += 1

        return RecoveryResult(scanned_cases=len(snapshots), enqueued_jobs=enqueued)


def _resolve_recovery_job(snapshot: CaseRecoverySnapshot) -> str | None:
    status = snapshot.status

    if status in {CaseStatus.R2_POST_WIDGET, CaseStatus.LLM_SUGGEST}:
        return "post_room2_widget"
    if status in {CaseStatus.DOCTOR_ACCEPTED, CaseStatus.R3_POST_REQUEST}:
        return "post_room3_request"
    if status == CaseStatus.DOCTOR_DENIED:
        return "post_room1_final_denial_triage"
    if status == CaseStatus.APPT_CONFIRMED:
        return "post_room1_final_appt"
    if status == CaseStatus.APPT_DENIED:
        return "post_room1_final_appt_denied"
    if status == CaseStatus.FAILED:
        return "post_room1_final_failure"
    if status == CaseStatus.CLEANUP_RUNNING:
        return "execute_cleanup"
    if (
        status == CaseStatus.WAIT_R1_CLEANUP_THUMBS
        and snapshot.cleanup_triggered_at is not None
        and snapshot.cleanup_completed_at is None
    ):
        return "execute_cleanup"

    return None
