"""SQLAlchemy query adapter for Room-4 supervisor summary aggregate metrics."""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from triage_automation.application.ports.supervisor_summary_metrics_query_port import (
    SupervisorSummaryMetrics,
    SupervisorSummaryMetricsQueryPort,
)
from triage_automation.domain.case_status import CaseStatus
from triage_automation.domain.monitoring_projection import (
    MonitoringCurrentStatus,
    MonitoringOperationalBranch,
    MonitoringPendingStage,
    MonitoringProjectionInput,
    derive_monitoring_projection,
)
from triage_automation.infrastructure.db.metadata import cases

case_report_transcripts = sa.table(
    "case_report_transcripts",
    sa.column("id", sa.Integer()),
    sa.column("captured_at", sa.DateTime(timezone=True)),
)


class SqlAlchemySupervisorSummaryMetricsQueries(SupervisorSummaryMetricsQueryPort):
    """Aggregate Room-4 summary counters from persisted case/report timestamps."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def aggregate_metrics(
        self,
        *,
        window_start: datetime,
        window_end: datetime,
    ) -> SupervisorSummaryMetrics:
        """Return aggregate counts in `[window_start, window_end)` using case/report fields."""

        patients_statement = sa.select(sa.func.count()).select_from(cases).where(
            cases.c.created_at >= window_start,
            cases.c.created_at < window_end,
        )
        reports_statement = sa.select(sa.func.count()).select_from(case_report_transcripts).where(
            case_report_transcripts.c.captured_at >= window_start,
            case_report_transcripts.c.captured_at < window_end,
        )
        evaluated_statement = sa.select(sa.func.count()).select_from(cases).where(
            cases.c.doctor_decided_at.is_not(None),
            cases.c.doctor_decided_at >= window_start,
            cases.c.doctor_decided_at < window_end,
        )
        accepted_scheduled_statement = sa.select(sa.func.count()).select_from(cases).where(
            cases.c.appointment_status == "confirmed",
            cases.c.appointment_decided_at.is_not(None),
            cases.c.appointment_decided_at >= window_start,
            cases.c.appointment_decided_at < window_end,
        )
        immediate_admission_statement = sa.select(sa.func.count()).select_from(cases).where(
            cases.c.doctor_decision == "accept",
            cases.c.doctor_admission_flow == "immediate",
            cases.c.room1_final_reply_event_id.is_not(None),
            cases.c.cleanup_triggered_at.is_not(None),
            cases.c.cleanup_triggered_at >= window_start,
            cases.c.cleanup_triggered_at < window_end,
        )

        doctor_denied_statement = sa.select(sa.func.count()).select_from(cases).where(
            cases.c.doctor_decision == "deny",
            cases.c.doctor_decided_at.is_not(None),
            cases.c.doctor_decided_at >= window_start,
            cases.c.doctor_decided_at < window_end,
        )
        scheduler_denied_statement = sa.select(sa.func.count()).select_from(cases).where(
            cases.c.appointment_status == "denied",
            cases.c.appointment_decided_at.is_not(None),
            cases.c.appointment_decided_at >= window_start,
            cases.c.appointment_decided_at < window_end,
        )
        backlog_rows_statement = sa.select(
            cases.c.status,
            cases.c.doctor_decision,
            cases.c.doctor_admission_flow,
            cases.c.appointment_status,
            cases.c.room1_final_reply_event_id,
        )

        async with self._session_factory() as session:
            patients_received = int((await session.execute(patients_statement)).scalar_one())
            reports_processed = int((await session.execute(reports_statement)).scalar_one())
            cases_evaluated = int((await session.execute(evaluated_statement)).scalar_one())
            accepted_scheduled = int(
                (await session.execute(accepted_scheduled_statement)).scalar_one()
            )
            immediate_admission = int(
                (await session.execute(immediate_admission_statement)).scalar_one()
            )
            doctor_denied = int((await session.execute(doctor_denied_statement)).scalar_one())
            scheduler_denied = int(
                (await session.execute(scheduler_denied_statement)).scalar_one()
            )
            backlog_rows = (await session.execute(backlog_rows_statement)).mappings().all()

        in_progress = 0
        pending_room2 = 0
        pending_room3 = 0
        pending_room1 = 0
        pending_immediate_branch = 0

        for row in backlog_rows:
            projection = derive_monitoring_projection(
                MonitoringProjectionInput(
                    status=CaseStatus(str(row["status"])),
                    doctor_decision=row["doctor_decision"],
                    doctor_admission_flow=row["doctor_admission_flow"],
                    appointment_status=row["appointment_status"],
                    room1_final_reply_event_id=row["room1_final_reply_event_id"],
                )
            )
            if projection.status_atual is MonitoringCurrentStatus.EM_ANDAMENTO:
                in_progress += 1
            if projection.etapa_pendente is MonitoringPendingStage.AGUARDANDO_SALA_2:
                pending_room2 += 1
            if projection.etapa_pendente is MonitoringPendingStage.AGUARDANDO_SALA_3:
                pending_room3 += 1
            if projection.etapa_pendente is MonitoringPendingStage.AGUARDANDO_SALA_1:
                pending_room1 += 1
            if (
                projection.status_atual is MonitoringCurrentStatus.EM_ANDAMENTO
                and projection.ramo_operacional is MonitoringOperationalBranch.VINDA_IMEDIATA
            ):
                pending_immediate_branch += 1

        return SupervisorSummaryMetrics(
            patients_received=patients_received,
            reports_processed=reports_processed,
            cases_evaluated=cases_evaluated,
            accepted_scheduled=accepted_scheduled,
            immediate_admission=immediate_admission,
            refused=doctor_denied + scheduler_denied,
            in_progress=in_progress,
            pending_room2=pending_room2,
            pending_room3=pending_room3,
            pending_room1=pending_room1,
            pending_immediate_branch=pending_immediate_branch,
        )
