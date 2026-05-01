"""Web workflow queue projections by operational role.

Provides role-specific filtered views over case card data:
- Doctor queue: cases in ``WAIT_DOCTOR`` status.
- Scheduler queue: cases in ``WAIT_APPT`` status.
- NIR queue: active/non-cleaned cases for the NIR operator.

Each projection returns a list of ``CaseCardFields`` ordered by
``latest_activity_at`` descending, giving the most recent cases first.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from triage_automation.domain.case_status import CaseStatus


@dataclass(frozen=True)
class CaseCardFields:
    """Minimal card fields for queue and list rendering across web surfaces.

    Attributes:
        case_id: Unique case identifier.
        status: Current case status from the state machine.
        latest_activity_at: Most recent activity timestamp (UTC).
        agency_record_number: Extracted agency record number, if available.
        patient_name: Extracted patient name, if available.
        compact_summary: Pre-built compact operational summary string.
    """

    case_id: UUID
    status: CaseStatus
    latest_activity_at: datetime
    agency_record_number: str | None = None
    patient_name: str | None = None
    compact_summary: str = "EM_ANDAMENTO"


@dataclass(frozen=True)
class DoctorQueueProjection:
    """Filtered queue of cases awaiting doctor decision."""

    items: list[CaseCardFields]


@dataclass(frozen=True)
class SchedulerQueueProjection:
    """Filtered queue of cases awaiting scheduling confirmation."""

    items: list[CaseCardFields]


@dataclass(frozen=True)
class NIRQueueProjection:
    """Filtered list of active/recent cases for the NIR operator."""

    items: list[CaseCardFields]


# Statuses visible in the NIR queue (all except fully cleaned).
_NIR_EXCLUDED_STATUSES: frozenset[CaseStatus] = frozenset({CaseStatus.CLEANED})


def derive_doctor_queue(cases: list[CaseCardFields]) -> DoctorQueueProjection:
    """Filter and sort cases for the doctor queue.

    Only cases in ``WAIT_DOCTOR`` status appear, ordered by most recent
    activity first.

    Args:
        cases: Full list of case cards to filter.

    Returns:
        A ``DoctorQueueProjection`` with matching cases.
    """
    filtered = [c for c in cases if c.status is CaseStatus.WAIT_DOCTOR]
    return DoctorQueueProjection(
        items=_sort_by_activity_desc(filtered),
    )


def derive_scheduler_queue(cases: list[CaseCardFields]) -> SchedulerQueueProjection:
    """Filter and sort cases for the scheduler queue.

    Only cases in ``WAIT_APPT`` status appear, ordered by most recent
    activity first.

    Args:
        cases: Full list of case cards to filter.

    Returns:
        A ``SchedulerQueueProjection`` with matching cases.
    """
    filtered = [c for c in cases if c.status is CaseStatus.WAIT_APPT]
    return SchedulerQueueProjection(
        items=_sort_by_activity_desc(filtered),
    )


def derive_nir_queue(cases: list[CaseCardFields]) -> NIRQueueProjection:
    """Filter and sort cases for the NIR case list.

    All non-cleaned cases appear, ordered by most recent activity first.

    Args:
        cases: Full list of case cards to filter.

    Returns:
        An ``NIRQueueProjection`` with active cases.
    """
    filtered = [c for c in cases if c.status not in _NIR_EXCLUDED_STATUSES]
    return NIRQueueProjection(
        items=_sort_by_activity_desc(filtered),
    )


def _sort_by_activity_desc(items: list[CaseCardFields]) -> list[CaseCardFields]:
    """Return items sorted by latest_activity_at descending (newest first)."""

    return sorted(items, key=lambda c: c.latest_activity_at, reverse=True)
