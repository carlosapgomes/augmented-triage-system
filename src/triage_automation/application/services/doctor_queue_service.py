"""Service for the Doctor web queue showing cases awaiting decision.

Provides a role-specific filtered view over cases in ``WAIT_DOCTOR`` status,
reusing the shared ``derive_doctor_queue`` projection from the domain layer.

The service fetches all cases with recent activity via the case repository,
then filters to only those awaiting doctor decision, ordered by most
recent activity first.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from triage_automation.application.ports.case_repository_port import (
    CaseMonitoringListFilter,
    CaseRepositoryPort,
)
from triage_automation.domain.web_workflow_projections import (
    CaseCardFields,
    derive_doctor_queue,
)


class DoctorQueueService:
    """Application service for the doctor queue web surface.

    Lists cases awaiting medical decision, with clinical summary fields
    for each entry.
    """

    def __init__(self, case_repository: CaseRepositoryPort) -> None:
        """Initialize the doctor queue service.

        Args:
            case_repository: The case repository for querying case data.
        """
        self._case_repository = case_repository

    async def list_pending_cases(self) -> list[CaseCardFields]:
        """List cases awaiting doctor decision, ordered by latest activity descending.

        Only cases in ``WAIT_DOCTOR`` status appear.

        Returns:
            A list of ``CaseCardFields`` for the doctor queue.
        """
        now = datetime.now(tz=UTC)
        filters = CaseMonitoringListFilter(
            status=None,
            activity_from=now - timedelta(days=365),
            activity_to=now + timedelta(days=1),
            page=1,
            page_size=1000,
        )
        page = await self._case_repository.list_cases_for_monitoring(filters=filters)

        # Convert monitoring list items to card fields
        cards: list[CaseCardFields] = []
        for item in page.items:
            cards.append(
                CaseCardFields(
                    case_id=item.case_id,
                    status=item.status,
                    latest_activity_at=item.latest_activity_at,
                    agency_record_number=item.agency_record_number,
                    patient_name=item.patient_name,
                    compact_summary=item.compact_operational_summary,
                )
            )

        # Filter using shared domain projection
        queue = derive_doctor_queue(cards)
        return queue.items
