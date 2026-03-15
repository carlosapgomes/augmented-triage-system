"""Shared operational monitoring projection derived from persisted case state."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from triage_automation.domain.case_status import CaseStatus

DoctorDecisionValue = Literal["accept", "deny"]
DoctorAdmissionFlowValue = Literal["scheduled", "immediate"]
AppointmentStatusValue = Literal["confirmed", "denied"]

_ROOM1_ACKNOWLEDGED_STATUSES = frozenset(
    {
        CaseStatus.CLEANUP_RUNNING,
        CaseStatus.CLEANED,
    }
)
_ROOM2_PENDING_STATUSES = frozenset(
    {
        CaseStatus.NEW,
        CaseStatus.R1_ACK_PROCESSING,
        CaseStatus.EXTRACTING,
        CaseStatus.LLM_STRUCT,
        CaseStatus.LLM_SUGGEST,
        CaseStatus.R2_POST_WIDGET,
        CaseStatus.WAIT_DOCTOR,
    }
)
_ROOM3_PENDING_STATUSES = frozenset(
    {
        CaseStatus.DOCTOR_ACCEPTED,
        CaseStatus.R3_POST_REQUEST,
        CaseStatus.WAIT_APPT,
    }
)
_ROOM1_PENDING_STATUSES = frozenset(
    {
        CaseStatus.DOCTOR_DENIED,
        CaseStatus.APPT_CONFIRMED,
        CaseStatus.APPT_DENIED,
        CaseStatus.FAILED,
        CaseStatus.R1_FINAL_REPLY_POSTED,
        CaseStatus.WAIT_R1_CLEANUP_THUMBS,
    }
)


class MonitoringCurrentStatus(StrEnum):
    """Current operational status rendered by monitoring surfaces."""

    EM_ANDAMENTO = "EM_ANDAMENTO"
    CONCLUIDO = "CONCLUIDO"


class MonitoringPendingStage(StrEnum):
    """Supervisor-facing stop-point taxonomy for in-progress cases."""

    AGUARDANDO_SALA_2 = "AGUARDANDO_SALA_2"
    AGUARDANDO_SALA_3 = "AGUARDANDO_SALA_3"
    AGUARDANDO_SALA_1 = "AGUARDANDO_SALA_1"
    CONCLUIDO = "CONCLUIDO"


class MonitoringOperationalBranch(StrEnum):
    """Operational branch chosen after medical decision, when applicable."""

    AGENDAMENTO = "AGENDAMENTO"
    VINDA_IMEDIATA = "VINDA_IMEDIATA"
    NAO_APLICAVEL = "NAO_APLICAVEL"
    INDISPONIVEL = "INDISPONIVEL"


class MonitoringFinalOutcome(StrEnum):
    """Final consolidated outcome shown only after Room-1 acknowledgment."""

    ACEITO = "ACEITO"
    VINDA_IMEDIATA = "VINDA_IMEDIATA"
    NEGADO = "NEGADO"
    INDISPONIVEL = "INDISPONIVEL"


@dataclass(frozen=True)
class MonitoringProjectionInput:
    """Persisted case fields required to derive shared monitoring semantics."""

    status: CaseStatus
    doctor_decision: DoctorDecisionValue | None = None
    doctor_admission_flow: DoctorAdmissionFlowValue | None = None
    appointment_status: AppointmentStatusValue | None = None
    room1_final_reply_event_id: str | None = None
    room1_final_acknowledged: bool | None = None


@dataclass(frozen=True)
class MonitoringProjection:
    """Shared operational observability projection for dashboard and Room-4."""

    status_atual: MonitoringCurrentStatus
    etapa_pendente: MonitoringPendingStage
    ramo_operacional: MonitoringOperationalBranch
    desfecho_final: MonitoringFinalOutcome | None


def build_compact_operational_summary(projection: MonitoringProjection) -> str:
    """Compose a deterministic compact summary for case-list rendering."""

    if projection.desfecho_final is not None:
        if (
            projection.desfecho_final is MonitoringFinalOutcome.ACEITO
            and projection.ramo_operacional is MonitoringOperationalBranch.AGENDAMENTO
        ):
            return (
                f"{projection.desfecho_final.value}"
                f" · {projection.ramo_operacional.value}"
            )
        return projection.desfecho_final.value

    return " · ".join(
        (
            projection.status_atual.value,
            projection.etapa_pendente.value,
            projection.ramo_operacional.value,
        )
    )


def derive_monitoring_projection(source: MonitoringProjectionInput) -> MonitoringProjection:
    """Derive monitoring semantics from persisted case state only.

    The projection intentionally separates current progress, stop point,
    operational branch, and final outcome so observability surfaces can remain
    aligned with runtime semantics without reinterpreting the workflow.
    """

    room1_acknowledged = _room1_acknowledged(source)
    ramo_operacional = _derive_operational_branch(source)
    status_atual = (
        MonitoringCurrentStatus.CONCLUIDO
        if room1_acknowledged
        else MonitoringCurrentStatus.EM_ANDAMENTO
    )
    etapa_pendente = (
        MonitoringPendingStage.CONCLUIDO
        if room1_acknowledged
        else _derive_pending_stage(source, ramo_operacional)
    )
    desfecho_final = (
        _derive_final_outcome(source, ramo_operacional) if room1_acknowledged else None
    )
    return MonitoringProjection(
        status_atual=status_atual,
        etapa_pendente=etapa_pendente,
        ramo_operacional=ramo_operacional,
        desfecho_final=desfecho_final,
    )


def _room1_acknowledged(source: MonitoringProjectionInput) -> bool:
    explicit_ack = source.room1_final_acknowledged
    if explicit_ack is not None:
        return explicit_ack
    return source.status in _ROOM1_ACKNOWLEDGED_STATUSES


def _derive_operational_branch(
    source: MonitoringProjectionInput,
) -> MonitoringOperationalBranch:
    if source.doctor_decision != "accept":
        return MonitoringOperationalBranch.NAO_APLICAVEL
    if source.doctor_admission_flow == "immediate":
        return MonitoringOperationalBranch.VINDA_IMEDIATA
    if source.doctor_admission_flow == "scheduled":
        return MonitoringOperationalBranch.AGENDAMENTO
    if source.appointment_status in {"confirmed", "denied"}:
        return MonitoringOperationalBranch.AGENDAMENTO
    if source.status in {
        CaseStatus.R3_POST_REQUEST,
        CaseStatus.WAIT_APPT,
        CaseStatus.APPT_CONFIRMED,
        CaseStatus.APPT_DENIED,
    }:
        return MonitoringOperationalBranch.AGENDAMENTO
    return MonitoringOperationalBranch.INDISPONIVEL


def _derive_pending_stage(
    source: MonitoringProjectionInput,
    ramo_operacional: MonitoringOperationalBranch,
) -> MonitoringPendingStage:
    if source.status in _ROOM2_PENDING_STATUSES:
        return MonitoringPendingStage.AGUARDANDO_SALA_2
    if source.status in _ROOM1_PENDING_STATUSES:
        return MonitoringPendingStage.AGUARDANDO_SALA_1
    if source.status in _ROOM3_PENDING_STATUSES:
        if ramo_operacional is MonitoringOperationalBranch.VINDA_IMEDIATA:
            return MonitoringPendingStage.AGUARDANDO_SALA_1
        return MonitoringPendingStage.AGUARDANDO_SALA_3
    return MonitoringPendingStage.AGUARDANDO_SALA_2


def _derive_final_outcome(
    source: MonitoringProjectionInput,
    ramo_operacional: MonitoringOperationalBranch,
) -> MonitoringFinalOutcome:
    if source.doctor_decision == "deny" or source.appointment_status == "denied":
        return MonitoringFinalOutcome.NEGADO
    if ramo_operacional is MonitoringOperationalBranch.VINDA_IMEDIATA:
        return MonitoringFinalOutcome.VINDA_IMEDIATA
    if source.appointment_status == "confirmed":
        return MonitoringFinalOutcome.ACEITO
    return MonitoringFinalOutcome.INDISPONIVEL
