"""Port for prior-case lookup used by Room-2 widget enrichment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID

PriorCaseDecision = Literal["deny_triage", "deny_appointment", "failed", "accepted"]


@dataclass(frozen=True)
class PriorCaseSummary:
    """Prior-case block embedded into Room-2 widget payload."""

    prior_case_id: UUID
    decided_at: datetime
    decision: PriorCaseDecision
    reason: str | None


@dataclass(frozen=True)
class PriorCaseContext:
    """Resolved prior-case enrichment fields for widget payload."""

    prior_case: PriorCaseSummary | None
    prior_denial_count_7d: int | None


class PriorCaseQueryPort(Protocol):
    """Prior-case lookup contract scoped to current case/record window."""

    async def lookup_recent_context(
        self,
        *,
        case_id: UUID,
        agency_record_number: str,
        now: datetime | None = None,
    ) -> PriorCaseContext:
        """Return most recent prior case and optional denial counter in the 7-day window."""
