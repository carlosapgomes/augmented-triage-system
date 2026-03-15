from __future__ import annotations

from triage_automation.domain.case_status import CaseStatus
from triage_automation.domain.monitoring_projection import (
    MonitoringCurrentStatus,
    MonitoringFinalOutcome,
    MonitoringOperationalBranch,
    MonitoringPendingStage,
    MonitoringProjectionInput,
    derive_monitoring_projection,
)


def test_projection_marks_scheduled_cases_as_pending_on_room3_until_final_ack() -> None:
    projection = derive_monitoring_projection(
        MonitoringProjectionInput(
            status=CaseStatus.WAIT_APPT,
            doctor_decision="accept",
            doctor_admission_flow="scheduled",
        )
    )

    assert projection.status_atual is MonitoringCurrentStatus.EM_ANDAMENTO
    assert projection.etapa_pendente is MonitoringPendingStage.AGUARDANDO_SALA_3
    assert projection.ramo_operacional is MonitoringOperationalBranch.AGENDAMENTO
    assert projection.desfecho_final is None


def test_projection_routes_immediate_branch_directly_to_room1_pending_stage() -> None:
    projection = derive_monitoring_projection(
        MonitoringProjectionInput(
            status=CaseStatus.DOCTOR_ACCEPTED,
            doctor_decision="accept",
            doctor_admission_flow="immediate",
        )
    )

    assert projection.status_atual is MonitoringCurrentStatus.EM_ANDAMENTO
    assert projection.etapa_pendente is MonitoringPendingStage.AGUARDANDO_SALA_1
    assert projection.ramo_operacional is MonitoringOperationalBranch.VINDA_IMEDIATA
    assert projection.desfecho_final is None


def test_projection_keeps_immediate_cases_in_progress_until_room1_acknowledges() -> None:
    projection = derive_monitoring_projection(
        MonitoringProjectionInput(
            status=CaseStatus.WAIT_R1_CLEANUP_THUMBS,
            doctor_decision="accept",
            doctor_admission_flow="immediate",
            room1_final_reply_event_id="$room1-final",
        )
    )

    assert projection.status_atual is MonitoringCurrentStatus.EM_ANDAMENTO
    assert projection.etapa_pendente is MonitoringPendingStage.AGUARDANDO_SALA_1
    assert projection.ramo_operacional is MonitoringOperationalBranch.VINDA_IMEDIATA
    assert projection.desfecho_final is None


def test_projection_marks_immediate_cases_as_final_only_after_room1_acknowledgement() -> None:
    projection = derive_monitoring_projection(
        MonitoringProjectionInput(
            status=CaseStatus.CLEANUP_RUNNING,
            doctor_decision="accept",
            doctor_admission_flow="immediate",
            room1_final_reply_event_id="$room1-final",
        )
    )

    assert projection.status_atual is MonitoringCurrentStatus.CONCLUIDO
    assert projection.etapa_pendente is MonitoringPendingStage.CONCLUIDO
    assert projection.ramo_operacional is MonitoringOperationalBranch.VINDA_IMEDIATA
    assert projection.desfecho_final is MonitoringFinalOutcome.VINDA_IMEDIATA


def test_projection_marks_denied_cases_with_no_operational_branch() -> None:
    projection = derive_monitoring_projection(
        MonitoringProjectionInput(
            status=CaseStatus.CLEANED,
            doctor_decision="deny",
            room1_final_reply_event_id="$room1-final",
        )
    )

    assert projection.status_atual is MonitoringCurrentStatus.CONCLUIDO
    assert projection.etapa_pendente is MonitoringPendingStage.CONCLUIDO
    assert projection.ramo_operacional is MonitoringOperationalBranch.NAO_APLICAVEL
    assert projection.desfecho_final is MonitoringFinalOutcome.NEGADO


def test_projection_uses_legacy_fallback_without_inferring_immediate_branch() -> None:
    projection = derive_monitoring_projection(
        MonitoringProjectionInput(
            status=CaseStatus.DOCTOR_ACCEPTED,
            doctor_decision="accept",
        )
    )

    assert projection.status_atual is MonitoringCurrentStatus.EM_ANDAMENTO
    assert projection.etapa_pendente is MonitoringPendingStage.AGUARDANDO_SALA_3
    assert projection.ramo_operacional is MonitoringOperationalBranch.INDISPONIVEL
    assert projection.desfecho_final is None
