"""Service for authenticated scheduler confirmation callback handling.

Wraps the core logic for confirming or denying a scheduling appointment
via the web form, reusing the existing compare-and-set
``apply_scheduler_decision_if_waiting`` from the case repository.

This service is Matrix-free — it does not post Room-3 acks or handle
message-based replies. It focuses purely on state check, CAS update,
audit persistence, and next-step job enqueue for the web workflow.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from triage_automation.application.ports.audit_repository_port import (
    AuditEventCreateInput,
    AuditRepositoryPort,
)
from triage_automation.application.ports.case_repository_port import (
    CaseRepositoryPort,
    SchedulerDecisionUpdateInput,
)
from triage_automation.application.ports.job_queue_port import JobEnqueueInput, JobQueuePort
from triage_automation.domain.case_status import CaseStatus

logger = logging.getLogger(__name__)


class HandleSchedulerConfirmationOutcome(StrEnum):
    """Outcomes returned by scheduler confirmation callback handling."""

    APPLIED = "applied"
    NOT_FOUND = "not_found"
    WRONG_STATE = "wrong_state"
    DUPLICATE_OR_RACE = "duplicate_or_race"


@dataclass(frozen=True)
class HandleSchedulerConfirmationResult:
    """Service outcome model for web view response mapping."""

    outcome: HandleSchedulerConfirmationOutcome


@dataclass(frozen=True)
class SchedulerConfirmationPayload:
    """Normalized web form payload for scheduler confirmation/denial.

    Attributes:
        case_id: The case being acted on.
        scheduler_user_id: The authenticated scheduler user identifier.
        appointment_status: ``"confirmed"`` or ``"denied"``.
        appointment_at: The confirmed appointment datetime (UTC), only for confirmed.
        appointment_location: The appointment location, only for confirmed.
        appointment_instructions: Optional instructions for the patient.
        appointment_reason: The denial reason, only for denied.
    """

    case_id: UUID
    scheduler_user_id: str
    appointment_status: str
    appointment_at: datetime | None = None
    appointment_location: str | None = None
    appointment_instructions: str | None = None
    appointment_reason: str | None = None


class HandleSchedulerConfirmationService:
    """Persist scheduler confirmation/denial and enqueue next workflow job.

    Reuses the same ``apply_scheduler_decision_if_waiting`` CAS contract
    already exercised by ``Room3ReplyService``, ensuring identical
    state-machine behavior between web and Matrix paths.
    """

    def __init__(
        self,
        *,
        case_repository: CaseRepositoryPort,
        audit_repository: AuditRepositoryPort,
        job_queue: JobQueuePort,
    ) -> None:
        """Initialize the scheduler confirmation service.

        Args:
            case_repository: The case repository for CAS updates.
            audit_repository: The audit repository for web event persistence.
            job_queue: The job queue for enqueuing downstream workflow jobs.
        """
        self._case_repository = case_repository
        self._audit_repository = audit_repository
        self._job_queue = job_queue

    async def handle(
        self,
        payload: SchedulerConfirmationPayload,
    ) -> HandleSchedulerConfirmationResult:
        """Apply a scheduler confirmation/denial when case is in WAIT_APPT.

        Args:
            payload: The normalized confirmation/denial payload from the web form.

        Returns:
            A ``HandleSchedulerConfirmationResult`` with the outcome status.
        """
        logger.info(
            "scheduler_confirmation_received case_id=%s scheduler_user_id=%s status=%s",
            payload.case_id,
            payload.scheduler_user_id,
            payload.appointment_status,
        )

        snapshot = await self._case_repository.get_case_doctor_decision_snapshot(
            case_id=payload.case_id
        )
        if snapshot is None:
            logger.info(
                "scheduler_confirmation_ignored_not_found case_id=%s",
                payload.case_id,
            )
            return HandleSchedulerConfirmationResult(
                outcome=HandleSchedulerConfirmationOutcome.NOT_FOUND
            )

        if snapshot.status != CaseStatus.WAIT_APPT:
            await self._audit_repository.append_event(
                AuditEventCreateInput(
                    case_id=payload.case_id,
                    actor_type="system",
                    event_type="SCHEDULER_CONFIRMATION_IGNORED_WRONG_STATE",
                    payload={
                        "current_status": snapshot.status.value,
                        "appointment_status": payload.appointment_status,
                    },
                )
            )
            logger.info(
                "scheduler_confirmation_ignored_wrong_state case_id=%s current_status=%s",
                payload.case_id,
                snapshot.status.value,
            )
            return HandleSchedulerConfirmationResult(
                outcome=HandleSchedulerConfirmationOutcome.WRONG_STATE
            )

        applied = await self._case_repository.apply_scheduler_decision_if_waiting(
            SchedulerDecisionUpdateInput(
                case_id=payload.case_id,
                scheduler_user_id=payload.scheduler_user_id,
                appointment_status=payload.appointment_status,
                appointment_at=payload.appointment_at,
                appointment_location=payload.appointment_location,
                appointment_instructions=payload.appointment_instructions,
                appointment_reason=payload.appointment_reason,
            )
        )
        if not applied:
            await self._audit_repository.append_event(
                AuditEventCreateInput(
                    case_id=payload.case_id,
                    actor_type="system",
                    event_type="SCHEDULER_CONFIRMATION_DUPLICATE_OR_RACE_IGNORED",
                    payload={"appointment_status": payload.appointment_status},
                )
            )
            return HandleSchedulerConfirmationResult(
                outcome=HandleSchedulerConfirmationOutcome.DUPLICATE_OR_RACE
            )

        await self._audit_repository.append_event(
            AuditEventCreateInput(
                case_id=payload.case_id,
                actor_type="system",
                event_type=(
                    "SCHEDULER_APPT_CONFIRMED"
                    if payload.appointment_status == "confirmed"
                    else "SCHEDULER_APPT_DENIED"
                ),
                payload={
                    "scheduler_user_id": payload.scheduler_user_id,
                    "appointment_status": payload.appointment_status,
                    "appointment_at": (
                        payload.appointment_at.isoformat()
                        if payload.appointment_at is not None
                        else None
                    ),
                    "appointment_location": payload.appointment_location,
                    "appointment_reason": payload.appointment_reason,
                },
            )
        )

        next_job = _next_job_type(appointment_status=payload.appointment_status)
        await self._job_queue.enqueue(
            JobEnqueueInput(
                case_id=payload.case_id,
                job_type=next_job,
                payload={},
            )
        )
        logger.info(
            "scheduler_confirmation_applied case_id=%s next_job=%s",
            payload.case_id,
            next_job,
        )

        await self._audit_repository.append_event(
            AuditEventCreateInput(
                case_id=payload.case_id,
                actor_type="system",
                event_type="JOB_ENQUEUED_NEXT_STEP",
                payload={
                    "job_type": next_job,
                    "appointment_status": payload.appointment_status,
                },
            )
        )

        return HandleSchedulerConfirmationResult(
            outcome=HandleSchedulerConfirmationOutcome.APPLIED
        )


def _next_job_type(*, appointment_status: str) -> str:
    """Return the next downstream job type for the given appointment status.

    Args:
        appointment_status: ``"confirmed"`` or ``"denied"``.

    Returns:
        The job type string to enqueue.
    """
    if appointment_status == "confirmed":
        return "post_room1_final_appt"
    return "post_room1_final_appt_denied"
