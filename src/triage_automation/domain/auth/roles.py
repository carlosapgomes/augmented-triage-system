"""Role enum definitions for admin and reader access control."""

from __future__ import annotations

from enum import StrEnum


class UnknownRoleError(ValueError):
    """Raised when a role value is not supported."""


class Role(StrEnum):
    """Supported user roles."""

    ADMIN = "admin"
    READER = "reader"

    @classmethod
    def from_value(cls, value: Role | str) -> Role:
        """Normalize a role input into the domain enum."""

        if isinstance(value, cls):
            return value

        try:
            return cls(value)
        except ValueError as exc:
            raise UnknownRoleError(f"Unknown role: {value}") from exc
