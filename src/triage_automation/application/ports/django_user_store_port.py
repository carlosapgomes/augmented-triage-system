"""Port for Django-backed user persistence used by the Django admin surface.

Defines the data contract between the application-layer
``DjangoUserManagementService`` and the Django ORM adapter
in the infrastructure layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DjangoUserItem:
    """Flat user representation for admin listing and audit."""

    pk: int
    email: str
    role: str
    is_active: bool


@dataclass(frozen=True)
class DjangoCreateUserRequest:
    """Application-layer create-user payload for the Django surface."""

    email: str
    password: str
    role: str  # raw role value (may be "reader" → mapped to "manager")


class DjangoUserStorePort(Protocol):
    """Repository contract for Django user persistence operations.

    Implementations (in the infrastructure layer) bridge between the
    application service and Django's ORM, keeping the application
    layer free of framework imports.
    """

    def list_users(self) -> list[DjangoUserItem]:
        """Return all users ordered deterministically."""

    def get_by_pk(self, *, pk: int) -> DjangoUserItem | None:
        """Return one user by primary key, or None."""

    def create_user(
        self, *, email: str, password: str, role: str
    ) -> DjangoUserItem:
        """Persist a new user account and return it."""

    def email_exists(self, *, email: str) -> bool:
        """Return True if a user with the given normalized email exists."""

    def update_role(self, *, pk: int, role: str) -> DjangoUserItem:
        """Persist a new role value for an existing user."""

    def set_active(self, *, pk: int, is_active: bool) -> DjangoUserItem:
        """Persist the active flag for an existing user."""

    def count_active_by_role(self, *, role: str) -> int:
        """Return the count of active users with the given role."""
