from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic.config import Config

from alembic import command
from triage_automation.application.ports.case_repository_port import CaseCreateInput
from triage_automation.domain.case_status import CaseStatus
from triage_automation.domain.monitoring_projection import (
    MonitoringCurrentStatus,
    MonitoringFinalOutcome,
    MonitoringOperationalBranch,
    MonitoringPendingStage,
    MonitoringProjectionInput,
    derive_monitoring_projection,
)
from triage_automation.infrastructure.db.case_repository import SqlAlchemyCaseRepository
from triage_automation.infrastructure.db.session import create_session_factory


def _upgrade_head(tmp_path: Path, filename: str) -> tuple[str, str]:
    db_path = tmp_path / filename
    sync_url = f"sqlite+pysqlite:///{db_path}"
    async_url = f"sqlite+aiosqlite:///{db_path}"

    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(alembic_config, "head")

    return sync_url, async_url


async def _create_case(async_url: str, *, case_id: UUID, origin_event_id: str) -> None:
    session_factory = create_session_factory(async_url)
    repository = SqlAlchemyCaseRepository(session_factory)
    await repository.create_case(
        CaseCreateInput(
            case_id=case_id,
            status=CaseStatus.NEW,
            room1_origin_room_id="!room1:example.org",
            room1_origin_event_id=origin_event_id,
            room1_sender_user_id="@human:example.org",
        )
    )


def _update_case_row(
    sync_url: str,
    *,
    case_id: UUID,
    status: CaseStatus,
    doctor_decision: str | None = None,
    doctor_admission_flow: str | None = None,
    appointment_status: str | None = None,
    room1_final_reply_event_id: str | None = None,
) -> None:
    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "UPDATE cases "
                "SET status = :status, "
                "doctor_decision = :doctor_decision, "
                "doctor_admission_flow = :doctor_admission_flow, "
                "appointment_status = :appointment_status, "
                "room1_final_reply_event_id = :room1_final_reply_event_id, "
                "updated_at = :updated_at "
                "WHERE case_id = :case_id"
            ),
            {
                "case_id": case_id.hex,
                "status": status.value,
                "doctor_decision": doctor_decision,
                "doctor_admission_flow": doctor_admission_flow,
                "appointment_status": appointment_status,
                "room1_final_reply_event_id": room1_final_reply_event_id,
                "updated_at": datetime(2026, 2, 18, 12, 0, tzinfo=UTC),
            },
        )


def _projection_from_persisted_row(sync_url: str, *, case_id: UUID) -> object:
    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        row = connection.execute(
            sa.text(
                "SELECT status, doctor_decision, doctor_admission_flow, "
                "appointment_status, room1_final_reply_event_id "
                "FROM cases WHERE case_id = :case_id"
            ),
            {"case_id": case_id.hex},
        ).mappings().one()

    return derive_monitoring_projection(
        MonitoringProjectionInput(
            status=CaseStatus(row["status"]),
            doctor_decision=row["doctor_decision"],
            doctor_admission_flow=row["doctor_admission_flow"],
            appointment_status=row["appointment_status"],
            room1_final_reply_event_id=row["room1_final_reply_event_id"],
        )
    )


@pytest.mark.asyncio
async def test_persisted_scheduled_case_projects_room3_pending_semantics(
    tmp_path: Path,
) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "monitoring_projection_scheduled.db")
    case_id = uuid4()
    await _create_case(async_url, case_id=case_id, origin_event_id="$origin-scheduled")
    _update_case_row(
        sync_url,
        case_id=case_id,
        status=CaseStatus.WAIT_APPT,
        doctor_decision="accept",
        doctor_admission_flow="scheduled",
    )

    projection = _projection_from_persisted_row(sync_url, case_id=case_id)

    assert projection.status_atual is MonitoringCurrentStatus.EM_ANDAMENTO
    assert projection.etapa_pendente is MonitoringPendingStage.AGUARDANDO_SALA_3
    assert projection.ramo_operacional is MonitoringOperationalBranch.AGENDAMENTO
    assert projection.desfecho_final is None


@pytest.mark.asyncio
async def test_persisted_immediate_case_projects_room1_pending_before_ack(
    tmp_path: Path,
) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "monitoring_projection_immediate_pending.db")
    case_id = uuid4()
    await _create_case(async_url, case_id=case_id, origin_event_id="$origin-immediate-pending")
    _update_case_row(
        sync_url,
        case_id=case_id,
        status=CaseStatus.WAIT_R1_CLEANUP_THUMBS,
        doctor_decision="accept",
        doctor_admission_flow="immediate",
        room1_final_reply_event_id="$room1-final-pending",
    )

    projection = _projection_from_persisted_row(sync_url, case_id=case_id)

    assert projection.status_atual is MonitoringCurrentStatus.EM_ANDAMENTO
    assert projection.etapa_pendente is MonitoringPendingStage.AGUARDANDO_SALA_1
    assert projection.ramo_operacional is MonitoringOperationalBranch.VINDA_IMEDIATA
    assert projection.desfecho_final is None


@pytest.mark.asyncio
async def test_persisted_immediate_case_projects_final_outcome_after_ack(
    tmp_path: Path,
) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "monitoring_projection_immediate_final.db")
    case_id = uuid4()
    await _create_case(async_url, case_id=case_id, origin_event_id="$origin-immediate-final")
    _update_case_row(
        sync_url,
        case_id=case_id,
        status=CaseStatus.CLEANED,
        doctor_decision="accept",
        doctor_admission_flow="immediate",
        room1_final_reply_event_id="$room1-final-complete",
    )

    projection = _projection_from_persisted_row(sync_url, case_id=case_id)

    assert projection.status_atual is MonitoringCurrentStatus.CONCLUIDO
    assert projection.etapa_pendente is MonitoringPendingStage.CONCLUIDO
    assert projection.ramo_operacional is MonitoringOperationalBranch.VINDA_IMEDIATA
    assert projection.desfecho_final is MonitoringFinalOutcome.VINDA_IMEDIATA


@pytest.mark.asyncio
async def test_persisted_denied_case_projects_negative_final_outcome(
    tmp_path: Path,
) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "monitoring_projection_denied.db")
    case_id = uuid4()
    await _create_case(async_url, case_id=case_id, origin_event_id="$origin-denied")
    _update_case_row(
        sync_url,
        case_id=case_id,
        status=CaseStatus.CLEANUP_RUNNING,
        doctor_decision="deny",
        room1_final_reply_event_id="$room1-final-denied",
    )

    projection = _projection_from_persisted_row(sync_url, case_id=case_id)

    assert projection.status_atual is MonitoringCurrentStatus.CONCLUIDO
    assert projection.etapa_pendente is MonitoringPendingStage.CONCLUIDO
    assert projection.ramo_operacional is MonitoringOperationalBranch.NAO_APLICAVEL
    assert projection.desfecho_final is MonitoringFinalOutcome.NEGADO


@pytest.mark.asyncio
async def test_persisted_legacy_case_uses_indisponivel_branch_fallback(
    tmp_path: Path,
) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "monitoring_projection_legacy.db")
    case_id = uuid4()
    await _create_case(async_url, case_id=case_id, origin_event_id="$origin-legacy")
    _update_case_row(
        sync_url,
        case_id=case_id,
        status=CaseStatus.DOCTOR_ACCEPTED,
        doctor_decision="accept",
    )

    projection = _projection_from_persisted_row(sync_url, case_id=case_id)

    assert projection.status_atual is MonitoringCurrentStatus.EM_ANDAMENTO
    assert projection.etapa_pendente is MonitoringPendingStage.AGUARDANDO_SALA_3
    assert projection.ramo_operacional is MonitoringOperationalBranch.INDISPONIVEL
    assert projection.desfecho_final is None
