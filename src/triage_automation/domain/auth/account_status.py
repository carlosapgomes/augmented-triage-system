"""Account status enum definitions for user lifecycle management."""

from __future__ import annotations

from enum import StrEnum


class UnknownAccountStatusError(ValueError):
    """Raised when an account status value is not supported."""


class AccountStatus(StrEnum):
    """Supported user account lifecycle statuses."""

    ACTIVE = "active"
    BLOCKED = "blocked"
    REMOVED = "removed"

    @classmethod
    def from_value(cls, value: AccountStatus | str) -> AccountStatus:
        """Normalize an account status input into the domain enum."""

        if isinstance(value, cls):
            return value

        try:
            return cls(value)
        except ValueError as exc:
            raise UnknownAccountStatusError(f"Unknown account status: {value}") from exc
