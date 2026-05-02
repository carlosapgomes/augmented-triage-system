"""Service for the NIR dashboard and case detail views.

Provides case listing (non-cleaned) and case detail with
operational progress information for NIR web users.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from triage_automation.application.ports.case_repository_port import (
    CaseMonitoringDetail,
    CaseMonitoringListFilter,
    CaseRepositoryPort,
)
from triage_automation.domain.case_status import CaseStatus


@dataclass(frozen=True)
class NirCaseCard:
    """Case card data for the NIR dashboard listing.

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


class NirDashboardService:
    """Application service for the NIR dashboard surface.

    Lists non-cleaned cases and retrieves case detail with timeline
    for the NIR operator web view.
    """

    def __init__(self, case_repository: CaseRepositoryPort) -> None:
        """Initialize the NIR dashboard service.

        Args:
            case_repository: The case repository for querying case data.
        """
        self._case_repository = case_repository

    async def list_nir_cases(self) -> list[NirCaseCard]:
        """List all non-cleaned cases ordered by latest activity descending.

        Returns:
            A list of ``NirCaseCard`` instances for the NIR dashboard.
        """
        from datetime import UTC

        now = datetime.now(tz=UTC)
        from datetime import timedelta

        # Use a wide date range to capture all cases
        filters = CaseMonitoringListFilter(
            status=None,
            activity_from=now - timedelta(days=365),
            activity_to=now + timedelta(days=1),
            page=1,
            page_size=1000,
        )
        page = await self._case_repository.list_cases_for_monitoring(filters=filters)

        # Filter out CLEANED cases (NIR only sees active ones)
        result: list[NirCaseCard] = []
        for item in page.items:
            if item.status == CaseStatus.CLEANED:
                continue
            result.append(
                NirCaseCard(
                    case_id=item.case_id,
                    status=item.status,
                    latest_activity_at=item.latest_activity_at,
                    compact_summary=item.compact_operational_summary,
                    patient_name=item.patient_name,
                    agency_record_number=item.agency_record_number,
                )
            )
        return result

    async def get_case_detail(self, case_id: UUID) -> CaseMonitoringDetail | None:
        """Retrieve case detail with timeline for the NIR case detail view.

        Args:
            case_id: The UUID of the case to retrieve.

        Returns:
            A ``CaseMonitoringDetail`` or ``None`` if the case does not exist.
        """
        return await self._case_repository.get_case_monitoring_detail(case_id=case_id)
