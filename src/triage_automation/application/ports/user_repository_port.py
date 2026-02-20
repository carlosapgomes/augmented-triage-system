"""Port for user persistence operations used by authentication and admin services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from triage_automation.domain.auth.account_status import AccountStatus
from triage_automation.domain.auth.roles import Role


@dataclass(frozen=True)
class UserRecord:
    """User persistence model."""

    user_id: UUID
    email: str
    password_hash: str
    role: Role
    is_active: bool
    created_at: datetime
    updated_at: datetime
    account_status: AccountStatus = AccountStatus.ACTIVE


@dataclass(frozen=True)
class UserCreateInput:
    """Input payload for creating a persisted user."""

    user_id: UUID
    email: str
    password_hash: str
    role: Role
    account_status: AccountStatus = AccountStatus.ACTIVE


class UserRepositoryPort(Protocol):
    """User repository contract."""

    async def get_by_id(self, *, user_id: UUID) -> UserRecord | None:
        """Return user by id, including inactive users."""

    async def get_by_email(self, *, email: str) -> UserRecord | None:
        """Return user by normalized email, including inactive users."""

    async def get_active_by_email(self, *, email: str) -> UserRecord | None:
        """Return active user by normalized email or None."""

    async def list_users(self) -> list[UserRecord]:
        """Return all users ordered for deterministic admin listing."""

    async def create_user(self, payload: UserCreateInput) -> UserRecord:
        """Persist one user account and return the inserted row."""

    async def set_account_status(
        self,
        *,
        user_id: UUID,
        account_status: AccountStatus,
    ) -> UserRecord | None:
        """Update user account status and return updated row."""
