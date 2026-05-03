"""Service for NIR final acknowledgment via web.

Provides the canonical human closure checkpoint for the web workflow,
replacing the Matrix Room-1 thumbs-up reaction with an explicit
web acknowledgment action by the NIR user.

When the NIR confirms receipt of the final result:
- The service calls ``claim_cleanup_trigger_if_first`` for idempotent CAS.
- Persists a ``NIR_FINAL_ACKNOWLEDGMENT`` web human audit event.
- Enqueues the ``execute_cleanup`` job to finalize the case.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from triage_automation.application.ports.audit_repository_port import (
    AuditEventCreateInput,
    AuditRepositoryPort,
)
from triage_automation.application.ports.case_repository_port import (
    CaseDoctorDecisionSnapshot,
    CaseRepositoryPort,
)
from triage_automation.application.ports.job_queue_port import JobEnqueueInput, JobQueuePort
from triage_automation.application.services.patient_context import extract_patient_name_age
from triage_automation.domain.case_status import CaseStatus
from triage_automation.domain.web_event_contract import WebEventOrigin, WebEventType

logger = logging.getLogger(__name__)


class NirFinalAcknowledgmentOutcome(StrEnum):
    """Outcomes returned by NIR final acknowledgment handling."""

    APPLIED = "applied"
    NOT_FOUND = "not_found"
    WRONG_STATE = "wrong_state"
    DUPLICATE_OR_RACE = "duplicate_or_race"


@dataclass(frozen=True)
class NirFinalAcknowledgmentResult:
    """Service outcome model for web view response mapping.

    Attributes:
        outcome: The acknowledgment result status.
    """

    outcome: NirFinalAcknowledgmentOutcome


@dataclass(frozen=True)
class NirAcknowledgmentCase:
    """Public DTO for the NIR acknowledgment view rendering.

    Carries the case context needed by the web adapter without
    exposing internal repository/snapshot types.

    Attributes:
        case_id: Unique case identifier.
        status: Current case status from the state machine.
        patient_name: Extracted patient name, if available.
        patient_age: Extracted patient age, if available.
        agency_record_number: Extracted agency record number, if available.
    """

    case_id: UUID
    status: CaseStatus
    patient_name: str | None = None
    patient_age: int | None = None
    agency_record_number: str | None = None


class NirFinalAcknowledgmentService:
    """Handle NIR final acknowledgment and trigger canonical closure.

    Replaces the Room-1 Matrix thumbs-up reaction as the canonical
    human cleanup trigger. Uses the same ``claim_cleanup_trigger_if_first``
    CAS contract exercised by ``ReactionService`` for deterministic,
    idempotent closure semantics.
    """

    def __init__(
        self,
        *,
        case_repository: CaseRepositoryPort,
        audit_repository: AuditRepositoryPort,
        job_queue: JobQueuePort,
    ) -> None:
        """Initialize the NIR final acknowledgment service.

        Args:
            case_repository: The case repository for CAS updates and queries.
            audit_repository: The audit repository for web event persistence.
            job_queue: The job queue for enqueuing the cleanup job.
        """
        self._case_repository = case_repository
        self._audit_repository = audit_repository
        self._job_queue = job_queue

    def get_acknowledgment_case(
        self,
        *,
        case_id: UUID,
    ) -> NirAcknowledgmentCase | None:
        """Load case context for the NIR acknowledgment view.

        Returns ``None`` when the case does not exist or is not in
        ``WAIT_R1_CLEANUP_THUMBS`` status (the only state where
        the NIR can submit the final acknowledgment).

        Args:
            case_id: The case identifier.

        Returns:
            A ``NirAcknowledgmentCase`` DTO or ``None``.
        """
        import asyncio

        return asyncio.run(self._get_acknowledgment_case_async(case_id=case_id))

    async def _get_acknowledgment_case_async(
        self,
        *,
        case_id: UUID,
    ) -> NirAcknowledgmentCase | None:
        """Async version of get_acknowledgment_case for internal use."""
        snapshot: CaseDoctorDecisionSnapshot | None = (
            await self._case_repository.get_case_doctor_decision_snapshot(
                case_id=case_id
            )
        )
        if snapshot is None:
            return None

        if snapshot.status != CaseStatus.WAIT_R1_CLEANUP_THUMBS:
            return None

        patient_name: str | None = None
        patient_age: int | None = None
        if snapshot.structured_data_json:
            patient_name, patient_age = extract_patient_name_age(  # type: ignore[assignment]
                snapshot.structured_data_json
            )

        return NirAcknowledgmentCase(
            case_id=case_id,
            status=snapshot.status,
            patient_name=patient_name,
            patient_age=patient_age,
            agency_record_number=snapshot.agency_record_number,
        )

    async def acknowledge(
        self,
        *,
        case_id: UUID,
        nir_user_id: str,
        actor_email: str,
    ) -> NirFinalAcknowledgmentResult:
        """Process NIR final acknowledgment and trigger cleanup.

        Validates the case is in ``WAIT_R1_CLEANUP_THUMBS``, then
        claims the cleanup trigger via CAS. Only the first successful
        claim results in audit persistence and job enqueue.

        Args:
            case_id: The case being acknowledged.
            nir_user_id: The authenticated NIR user identifier.
            actor_email: The authenticated NIR email for audit.

        Returns:
            A ``NirFinalAcknowledgmentResult`` with the outcome status.
        """
        logger.info(
            "nir_final_acknowledgment_received case_id=%s nir_user_id=%s",
            case_id,
            nir_user_id,
        )

        snapshot = await self._case_repository.get_case_doctor_decision_snapshot(
            case_id=case_id
        )
        if snapshot is None:
            logger.info(
                "nir_final_acknowledgment_ignored_not_found case_id=%s",
                case_id,
            )
            return NirFinalAcknowledgmentResult(
                outcome=NirFinalAcknowledgmentOutcome.NOT_FOUND
            )

        if snapshot.status != CaseStatus.WAIT_R1_CLEANUP_THUMBS:
            await self._audit_repository.append_event(
                AuditEventCreateInput(
                    case_id=case_id,
                    actor_type="system",
                    event_type="NIR_FINAL_ACK_IGNORED_WRONG_STATE",
                    payload={
                        "current_status": snapshot.status.value,
                        "nir_user_id": nir_user_id,
                    },
                )
            )
            logger.info(
                "nir_final_acknowledgment_ignored_wrong_state case_id=%s current_status=%s",
                case_id,
                snapshot.status.value,
            )
            return NirFinalAcknowledgmentResult(
                outcome=NirFinalAcknowledgmentOutcome.WRONG_STATE
            )

        claimed = await self._case_repository.claim_cleanup_trigger_if_first(
            case_id=case_id,
            reactor_user_id=nir_user_id,
        )
        if not claimed:
            await self._audit_repository.append_event(
                AuditEventCreateInput(
                    case_id=case_id,
                    actor_type="system",
                    event_type="NIR_FINAL_ACK_DUPLICATE_OR_RACE_IGNORED",
                    payload={"nir_user_id": nir_user_id},
                )
            )
            logger.info(
                "nir_final_acknowledgment_duplicate_or_race case_id=%s",
                case_id,
            )
            return NirFinalAcknowledgmentResult(
                outcome=NirFinalAcknowledgmentOutcome.DUPLICATE_OR_RACE
            )

        # Persist the web human acknowledgment event.
        from datetime import UTC, datetime

        await self._audit_repository.append_event(
            AuditEventCreateInput(
                case_id=case_id,
                actor_type="web_human",
                event_type=WebEventType.NIR_FINAL_ACKNOWLEDGMENT.value,
                actor_user_id=nir_user_id,
                payload={
                    "origin": WebEventOrigin.WEB.value,
                    "actor": actor_email,
                    "event_type": WebEventType.NIR_FINAL_ACKNOWLEDGMENT.value,
                    "summary_text": (
                        f"NIR final acknowledgment by {actor_email}"
                    ),
                    "timestamp": datetime.now(tz=UTC).isoformat(),
                },
            )
        )

        # Persist the system trigger audit event.
        await self._audit_repository.append_event(
            AuditEventCreateInput(
                case_id=case_id,
                actor_type="system",
                event_type="NIR_FINAL_ACK_TRIGGERED_CLEANUP",
                payload={
                    "nir_user_id": nir_user_id,
                    "actor_email": actor_email,
                },
            )
        )

        # Enqueue the cleanup job.
        await self._job_queue.enqueue(
            JobEnqueueInput(
                case_id=case_id,
                job_type="execute_cleanup",
                payload={},
            )
        )

        logger.info("nir_final_acknowledgment_applied case_id=%s", case_id)

        return NirFinalAcknowledgmentResult(
            outcome=NirFinalAcknowledgmentOutcome.APPLIED
        )
