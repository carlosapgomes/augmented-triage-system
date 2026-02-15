"""Port for append-only authentication audit event persistence."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID


@dataclass(frozen=True)
class AuthEventCreateInput:
    """Input payload for inserting an auth event."""

    event_type: str
    user_id: UUID | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


class AuthEventRepositoryPort(Protocol):
    """Auth event append contract."""

    async def append_event(self, payload: AuthEventCreateInput) -> int:
        """Append auth event and return numeric id."""
