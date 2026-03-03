from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import cast

import pytest

from triage_automation.application.ports.case_repository_port import (
    CaseMonitoringListFilter,
    CaseMonitoringListPage,
    CaseMonitoringOutcomeTotals,
    CaseRepositoryPort,
)
from triage_automation.application.services.case_monitoring_service import (
    CaseMonitoringListQuery,
    CaseMonitoringService,
)
from triage_automation.domain.case_status import CaseStatus


@dataclass
class _RecordingCaseRepository:
    """Test double that records list filters and returns a fixed page."""

    page: CaseMonitoringListPage
    captured_filters: CaseMonitoringListFilter | None = None

    async def list_cases_for_monitoring(
        self,
        *,
        filters: CaseMonitoringListFilter,
    ) -> CaseMonitoringListPage:
        self.captured_filters = filters
        return self.page


@pytest.mark.asyncio
async def test_case_monitoring_service_propagates_repository_totals_and_filters() -> None:
    """Preserva filtros e repassa totais agregados retornados pelo repositório."""

    expected_page = CaseMonitoringListPage(
        items=[],
        page=1,
        page_size=10,
        total=3,
        totals=CaseMonitoringOutcomeTotals(
            total=3,
            accepted=1,
            denied=1,
            in_progress=1,
        ),
    )
    repository = _RecordingCaseRepository(page=expected_page)
    service = CaseMonitoringService(
        case_repository=cast(CaseRepositoryPort, repository),
    )

    result = await service.list_cases(
        CaseMonitoringListQuery(
            page=1,
            page_size=10,
            status=CaseStatus.WAIT_DOCTOR,
            from_date=date(2026, 2, 18),
            to_date=date(2026, 2, 18),
            tz_offset_minutes=-180,
        )
    )

    assert result == expected_page
    assert result.totals.total == 3
    assert result.totals.accepted == 1
    assert result.totals.denied == 1
    assert result.totals.in_progress == 1

    assert repository.captured_filters is not None
    assert repository.captured_filters.status is CaseStatus.WAIT_DOCTOR
    assert repository.captured_filters.page == 1
    assert repository.captured_filters.page_size == 10
    assert repository.captured_filters.activity_from == datetime(2026, 2, 18, 3, 0, tzinfo=UTC)
    assert repository.captured_filters.activity_to == datetime(2026, 2, 19, 3, 0, tzinfo=UTC)
