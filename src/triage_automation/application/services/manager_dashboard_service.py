"""Service for the manager/admin consolidated operational dashboard.

Provides case listing with filters, pagination, and operational totals
for manager and admin supervisory roles.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from triage_automation.application.ports.case_repository_port import (
    CaseMonitoringDetail,
    CaseMonitoringListItem,
    CaseMonitoringListPage,
    CaseMonitoringOutcomeTotals,
    CaseRepositoryPort,
)
from triage_automation.application.services.case_monitoring_service import (
    CaseMonitoringListQuery,
    CaseMonitoringService,
)
from triage_automation.domain.case_status import CaseStatus
from triage_automation.domain.monitoring_projection import (
    MonitoringCurrentStatus,
    MonitoringFinalOutcome,
    MonitoringOperationalBranch,
    MonitoringPendingStage,
)


@dataclass(frozen=True)
class ManagerCaseCard:
    """Case card data for the manager/admin dashboard listing.

    Attributes:
        case_id: Unique case identifier.
        status: Current case status from the state machine.
        latest_activity_at: Most recent activity timestamp (UTC).
        compact_summary: Pre-built compact operational summary string.
        patient_name: Extracted patient name, if available.
        agency_record_number: Extracted agency record number, if available.
    """

    case_id: UUID
    status: CaseStatus
    latest_activity_at: datetime
    compact_summary: str = "EM_ANDAMENTO"
    patient_name: str | None = None
    agency_record_number: str | None = None


@dataclass(frozen=True)
class ManagerDashboardPage:
    """Manager dashboard page with cases and operational totals.

    Attributes:
        cases: List of case cards for the current page.
        page: Current page number.
        page_size: Number of cases per page.
        total: Total number of cases matching the filters.
        totals: Aggregated operational outcome totals.
    """

    cases: list[ManagerCaseCard]
    page: int
    page_size: int
    total: int
    totals: CaseMonitoringOutcomeTotals


class ManagerDashboardService:
    """Application service for the manager/admin consolidated dashboard.

    Lists all cases (including CLEANED) with filters, pagination,
    and operational totals for supervisory roles.
    """

    def __init__(self, case_repository: CaseRepositoryPort) -> None:
        """Initialize the manager dashboard service.

        Args:
            case_repository: The case repository for querying case data.
        """
        self._monitoring = CaseMonitoringService(case_repository=case_repository)

    async def list_cases(
        self,
        *,
        page: int = 1,
        page_size: int = 10,
        status: CaseStatus | None = None,
        status_atual: MonitoringCurrentStatus | None = None,
        etapa_pendente: MonitoringPendingStage | None = None,
        ramo_operacional: MonitoringOperationalBranch | None = None,
        desfecho_final: MonitoringFinalOutcome | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        tz_offset_minutes: int = 0,
    ) -> ManagerDashboardPage:
        """List cases with filters, pagination, and operational totals.

        Args:
            page: Page number (1-based).
            page_size: Number of cases per page.
            status: Filter by case status.
            status_atual: Filter by current monitoring status.
            etapa_pendente: Filter by pending stage.
            ramo_operacional: Filter by operational branch.
            desfecho_final: Filter by final outcome.
            from_date: Start date for activity filter (client-local).
            to_date: End date for activity filter (client-local).
            tz_offset_minutes: Client timezone offset in minutes.

        Returns:
            A ``ManagerDashboardPage`` with cases, pagination info, and totals.
        """
        query = CaseMonitoringListQuery(
            page=page,
            page_size=page_size,
            status=status,
            status_atual=status_atual,
            etapa_pendente=etapa_pendente,
            ramo_operacional=ramo_operacional,
            desfecho_final=desfecho_final,
            from_date=from_date,
            to_date=to_date,
            tz_offset_minutes=tz_offset_minutes,
        )
        page_result: CaseMonitoringListPage = await self._monitoring.list_cases(query)

        cases: list[ManagerCaseCard] = []
        for item in page_result.items:
            cases.append(_to_manager_card(item))

        return ManagerDashboardPage(
            cases=cases,
            page=page_result.page,
            page_size=page_result.page_size,
            total=page_result.total,
            totals=page_result.totals,
        )

    async def get_case_detail(self, case_id: UUID) -> CaseMonitoringDetail | None:
        """Retrieve case detail with timeline for the manager case detail view.

        Args:
            case_id: The UUID of the case to retrieve.

        Returns:
            A ``CaseMonitoringDetail`` or ``None`` if the case does not exist.
        """
        return await self._monitoring.get_case_detail(case_id=case_id)


def _to_manager_card(item: CaseMonitoringListItem) -> ManagerCaseCard:
    """Convert a monitoring list item to a manager case card.

    Args:
        item: The case monitoring list item from the repository.

    Returns:
        A ``ManagerCaseCard`` with the relevant fields.
    """
    return ManagerCaseCard(
        case_id=item.case_id,
        status=item.status,
        latest_activity_at=item.latest_activity_at,
        compact_summary=item.compact_operational_summary,
        patient_name=item.patient_name,
        agency_record_number=item.agency_record_number,
    )
