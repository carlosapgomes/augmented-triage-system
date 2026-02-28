"""Port for idempotent Room-4 supervisor summary dispatch persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

SupervisorSummaryDispatchStatus = Literal["pending", "sent", "failed"]


@dataclass(frozen=True)
class SupervisorSummaryWindowKey:
    """Unique Room-4 summary identity based on room and reporting window."""

    room_id: str
    window_start: datetime
    window_end: datetime


@dataclass(frozen=True)
class SupervisorSummaryDispatchSentInput:
    """Payload to mark one claimed Room-4 summary dispatch as successfully sent."""

    room_id: str
    window_start: datetime
    window_end: datetime
    matrix_event_id: str
    sent_at: datetime


@dataclass(frozen=True)
class SupervisorSummaryDispatchRecord:
    """Persisted Room-4 summary dispatch row exposed across repository boundaries."""

    dispatch_id: int
    room_id: str
    window_start: datetime
    window_end: datetime
    status: SupervisorSummaryDispatchStatus
    sent_at: datetime | None
    matrix_event_id: str | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class SupervisorSummaryDispatchRepositoryPort(Protocol):
    """Async contract for idempotent Room-4 summary dispatch tracking."""

    async def claim_window(self, payload: SupervisorSummaryWindowKey) -> bool:
        """Atomically claim dispatch execution for room/window; return whether claimed."""

    async def mark_sent(self, payload: SupervisorSummaryDispatchSentInput) -> bool:
        """CAS transition from pending to sent for room/window; return whether changed."""

    async def get_by_window(
        self,
        *,
        room_id: str,
        window_start: datetime,
        window_end: datetime,
    ) -> SupervisorSummaryDispatchRecord | None:
        """Load one dispatch row by room/window identity."""
