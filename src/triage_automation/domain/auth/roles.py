"""Role enum definitions for admin and reader access control."""

from __future__ import annotations

from enum import StrEnum


class UnknownRoleError(ValueError):
    """Raised when a role value is not supported."""


class Role(StrEnum):
    """Supported user roles.

    Includes legacy roles (reader, admin) and the full operational set
    (nir, doctor, scheduler, manager, admin) for the consolidated model.
    """

    ADMIN = "admin"
    READER = "reader"
    NIR = "nir"
    DOCTOR = "doctor"
    SCHEDULER = "scheduler"
    MANAGER = "manager"

    @classmethod
    def from_value(cls, value: Role | str) -> Role:
        """Normalize a role input into the domain enum."""

        if isinstance(value, cls):
            return value

        try:
            return cls(value)
        except ValueError as exc:
            raise UnknownRoleError(f"Unknown role: {value}") from exc
