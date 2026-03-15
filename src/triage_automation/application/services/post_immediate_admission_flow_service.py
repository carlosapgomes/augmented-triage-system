"""Service for posting Room-3 immediate-admission informational messages."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from triage_automation.application.ports.audit_repository_port import (
    AuditEventCreateInput,
    AuditRepositoryPort,
)
from triage_automation.application.ports.case_repository_port import CaseRepositoryPort
from triage_automation.application.ports.message_repository_port import (
    CaseMatrixMessageTranscriptCreateInput,
    CaseMessageCreateInput,
    MessageRepositoryPort,
)
from triage_automation.application.services.patient_context import (
    extract_patient_name_age,
    extract_pediatric_flag,
    extract_requested_exam,
    extract_supported_eda_subtype,
)
from triage_automation.domain.case_status import CaseStatus
from triage_automation.infrastructure.matrix.message_templates import (
    build_room3_immediate_admission_ack_message,
    build_room3_immediate_admission_message,
)

logger = logging.getLogger(__name__)


class MatrixRoomPosterPort(Protocol):
    """Port used to post standard text messages into Matrix rooms."""

    async def send_text(self, *, room_id: str, body: str) -> str:
        """Post text body to a room and return generated matrix event id."""

    async def reply_text(self, *, room_id: str, event_id: str, body: str) -> str:
        """Post text body as reply to a room event and return matrix event id."""


@dataclass
class PostImmediateAdmissionFlowRetriableError(RuntimeError):
    """Retriable posting error with explicit failure cause category."""

    cause: str
    details: str

    def __str__(self) -> str:
        return f"{self.cause}: {self.details}"


@dataclass(frozen=True)
class PostImmediateAdmissionFlowResult:
    """Outcome model for immediate-admission Room-3 posting."""

    posted: bool
    reason: str | None = None


class PostImmediateAdmissionFlowService:
    """Post Room-3 informational messages for doctor-approved immediate admissions."""

    def __init__(
        self,
        *,
        room3_id: str,
        case_repository: CaseRepositoryPort,
        audit_repository: AuditRepositoryPort,
        message_repository: MessageRepositoryPort,
        matrix_poster: MatrixRoomPosterPort,
    ) -> None:
        self._room3_id = room3_id
        self._case_repository = case_repository
        self._audit_repository = audit_repository
        self._message_repository = message_repository
        self._matrix_poster = matrix_poster

    async def post(self, *, case_id: UUID) -> PostImmediateAdmissionFlowResult:
        """Post Room-3 immediate-admission info plus audit-only acknowledgment target."""

        logger.info("room3_immediate_flow_post_started case_id=%s", case_id)
        snapshot = await self._case_repository.get_case_doctor_decision_snapshot(case_id=case_id)
        if snapshot is None:
            raise PostImmediateAdmissionFlowRetriableError(
                cause="room3_immediate",
                details="Case not found",
            )

        if snapshot.status != CaseStatus.DOCTOR_ACCEPTED:
            raise PostImmediateAdmissionFlowRetriableError(
                cause="room3_immediate",
                details=(
                    f"Case status {snapshot.status.value} is not ready for immediate admission post"
                ),
            )
        if snapshot.doctor_admission_flow != "immediate":
            raise PostImmediateAdmissionFlowRetriableError(
                cause="room3_immediate",
                details="Case is not marked for immediate admission flow",
            )

        existing_info_event_id = await self._message_repository.get_message_event_id_by_kind(
            case_id=case_id,
            room_id=self._room3_id,
            kind="room3_immediate_info",
        )
        existing_ack_event_id = await self._message_repository.get_message_event_id_by_kind(
            case_id=case_id,
            room_id=self._room3_id,
            kind="room3_immediate_ack",
        )
        if existing_ack_event_id is not None:
            await self._audit_repository.append_event(
                AuditEventCreateInput(
                    case_id=case_id,
                    actor_type="system",
                    event_type="ROOM3_IMMEDIATE_POST_SKIPPED_ALREADY_POSTED",
                    payload={
                        "status": snapshot.status.value,
                        "ack_event_id": existing_ack_event_id,
                    },
                )
            )
            logger.info(
                "room3_immediate_flow_post_skipped case_id=%s reason=already_posted",
                case_id,
            )
            return PostImmediateAdmissionFlowResult(posted=False, reason="already_posted")

        patient_name, patient_age = extract_patient_name_age(snapshot.structured_data_json)
        requested_exam = extract_requested_exam(snapshot.structured_data_json)
        supported_eda_subtype = extract_supported_eda_subtype(snapshot.structured_data_json)
        pediatric_flag = extract_pediatric_flag(snapshot.structured_data_json)

        info_body = build_room3_immediate_admission_message(
            agency_record_number=snapshot.agency_record_number,
            patient_name=patient_name,
            patient_age=patient_age,
            requested_exam=requested_exam,
            doctor_display_name=snapshot.doctor_display_name,
            support_flag=snapshot.doctor_support_flag,
            supported_eda_subtype=supported_eda_subtype,
            pediatric_flag=pediatric_flag,
        )

        info_event_id = existing_info_event_id
        if info_event_id is None:
            try:
                info_event_id = await self._matrix_poster.send_text(
                    room_id=self._room3_id,
                    body=info_body,
                )
            except Exception as exc:  # pragma: no cover - defensive resilience path
                logger.warning(
                    "room3_immediate_info_post_failed case_id=%s error=%s",
                    case_id,
                    exc,
                )
                await self._audit_repository.append_event(
                    AuditEventCreateInput(
                        case_id=case_id,
                        actor_type="system",
                        room_id=self._room3_id,
                        event_type="ROOM3_IMMEDIATE_INFO_POST_FAILED",
                        payload={"error": str(exc)},
                    )
                )
                return PostImmediateAdmissionFlowResult(
                    posted=False,
                    reason="info_post_failed",
                )
            await self._message_repository.add_message(
                CaseMessageCreateInput(
                    case_id=case_id,
                    room_id=self._room3_id,
                    event_id=info_event_id,
                    sender_user_id=None,
                    kind="room3_immediate_info",
                )
            )
            await self._message_repository.append_case_matrix_message_transcript(
                CaseMatrixMessageTranscriptCreateInput(
                    case_id=case_id,
                    room_id=self._room3_id,
                    event_id=info_event_id,
                    sender="bot",
                    message_type="room3_immediate_info",
                    message_text=info_body,
                )
            )
            await self._audit_repository.append_event(
                AuditEventCreateInput(
                    case_id=case_id,
                    actor_type="bot",
                    room_id=self._room3_id,
                    matrix_event_id=info_event_id,
                    event_type="ROOM3_IMMEDIATE_INFO_POSTED",
                    payload={},
                )
            )
        else:
            await self._audit_repository.append_event(
                AuditEventCreateInput(
                    case_id=case_id,
                    actor_type="system",
                    room_id=self._room3_id,
                    matrix_event_id=info_event_id,
                    event_type="ROOM3_IMMEDIATE_PARTIAL_PROGRESS_RESUMED",
                    payload={"resume_from": "info_posted_ack_missing"},
                )
            )

        ack_body = build_room3_immediate_admission_ack_message(
            agency_record_number=snapshot.agency_record_number,
            patient_name=patient_name,
            patient_age=patient_age,
            requested_exam=requested_exam,
            doctor_display_name=snapshot.doctor_display_name,
            support_flag=snapshot.doctor_support_flag,
            supported_eda_subtype=supported_eda_subtype,
            pediatric_flag=pediatric_flag,
        )
        try:
            ack_event_id = await self._matrix_poster.reply_text(
                room_id=self._room3_id,
                event_id=info_event_id,
                body=ack_body,
            )
        except Exception as exc:  # pragma: no cover - defensive resilience path
            logger.warning(
                "room3_immediate_ack_post_failed case_id=%s info_event_id=%s error=%s",
                case_id,
                info_event_id,
                exc,
            )
            await self._audit_repository.append_event(
                AuditEventCreateInput(
                    case_id=case_id,
                    actor_type="system",
                    room_id=self._room3_id,
                    matrix_event_id=info_event_id,
                    event_type="ROOM3_IMMEDIATE_ACK_POST_FAILED",
                    payload={"error": str(exc), "reply_to_event_id": info_event_id},
                )
            )
            return PostImmediateAdmissionFlowResult(posted=False, reason="ack_post_failed")
        await self._message_repository.add_message(
            CaseMessageCreateInput(
                case_id=case_id,
                room_id=self._room3_id,
                event_id=ack_event_id,
                sender_user_id=None,
                kind="room3_immediate_ack",
            )
        )
        await self._message_repository.append_case_matrix_message_transcript(
            CaseMatrixMessageTranscriptCreateInput(
                case_id=case_id,
                room_id=self._room3_id,
                event_id=ack_event_id,
                sender="bot",
                message_type="room3_immediate_ack",
                message_text=ack_body,
                reply_to_event_id=info_event_id,
            )
        )
        await self._audit_repository.append_event(
            AuditEventCreateInput(
                case_id=case_id,
                actor_type="bot",
                room_id=self._room3_id,
                matrix_event_id=ack_event_id,
                event_type="ROOM3_IMMEDIATE_ACK_POSTED",
                payload={"reply_to_event_id": info_event_id},
            )
        )

        logger.info(
            (
                "room3_immediate_flow_post_completed case_id=%s room_id=%s "
                "info_event_id=%s ack_event_id=%s"
            ),
            case_id,
            self._room3_id,
            info_event_id,
            ack_event_id,
        )
        return PostImmediateAdmissionFlowResult(posted=True)
