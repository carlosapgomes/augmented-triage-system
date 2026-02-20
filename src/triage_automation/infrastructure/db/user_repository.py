"""SQLAlchemy adapter for user persistence queries."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from triage_automation.application.ports.user_repository_port import (
    UserCreateInput,
    UserRecord,
    UserRepositoryPort,
)
from triage_automation.domain.auth.account_status import AccountStatus
from triage_automation.domain.auth.roles import Role
from triage_automation.infrastructure.db.metadata import users


class SqlAlchemyUserRepository(UserRepositoryPort):
    """User repository backed by SQLAlchemy async sessions."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_by_id(self, *, user_id: UUID) -> UserRecord | None:
        """Return user by id, including inactive users."""

        statement = sa.select(*_user_columns()).where(users.c.id == user_id).limit(1)

        async with self._session_factory() as session:
            result = await session.execute(statement)

        row = result.mappings().first()
        if row is None:
            return None
        return _to_user_record(row)

    async def get_by_email(self, *, email: str) -> UserRecord | None:
        """Return user by normalized email, including inactive users."""

        statement = sa.select(*_user_columns()).where(users.c.email == email).limit(1)

        async with self._session_factory() as session:
            result = await session.execute(statement)

        row = result.mappings().first()
        if row is None:
            return None
        return _to_user_record(row)

    async def get_active_by_email(self, *, email: str) -> UserRecord | None:
        """Return active user by normalized email or None."""

        user = await self.get_by_email(email=email)
        if user is None or not user.is_active:
            return None
        return user

    async def list_users(self) -> list[UserRecord]:
        """Return all users ordered for deterministic admin listing."""

        statement = sa.select(*_user_columns()).order_by(users.c.email.asc())

        async with self._session_factory() as session:
            result = await session.execute(statement)

        return [_to_user_record(row) for row in result.mappings().all()]

    async def create_user(self, payload: UserCreateInput) -> UserRecord:
        """Persist one user account and return the inserted row."""

        statement = (
            sa.insert(users)
            .values(
                id=payload.user_id,
                email=payload.email,
                password_hash=payload.password_hash,
                role=payload.role.value,
                is_active=_status_to_is_active(payload.account_status),
                account_status=payload.account_status.value,
            )
            .returning(*_user_columns())
        )

        async with self._session_factory() as session:
            result = await session.execute(statement)
            await session.commit()

        return _to_user_record(result.mappings().one())

    async def set_account_status(
        self,
        *,
        user_id: UUID,
        account_status: AccountStatus,
    ) -> UserRecord | None:
        """Update user account status and return updated row."""

        statement = (
            sa.update(users)
            .where(users.c.id == user_id)
            .values(
                account_status=account_status.value,
                is_active=_status_to_is_active(account_status),
                updated_at=sa.text("CURRENT_TIMESTAMP"),
            )
            .returning(*_user_columns())
        )

        async with self._session_factory() as session:
            result = await session.execute(statement)
            await session.commit()

        row = result.mappings().first()
        if row is None:
            return None
        return _to_user_record(row)


def _to_user_record(row: sa.RowMapping) -> UserRecord:
    raw_user_id = row["id"]
    user_id = raw_user_id if isinstance(raw_user_id, UUID) else UUID(str(raw_user_id))
    raw_status = row["account_status"] if "account_status" in row else AccountStatus.ACTIVE.value
    return UserRecord(
        user_id=user_id,
        email=cast(str, row["email"]),
        password_hash=cast(str, row["password_hash"]),
        role=Role(cast(str, row["role"])),
        is_active=bool(row["is_active"]),
        created_at=cast(datetime, row["created_at"]),
        updated_at=cast(datetime, row["updated_at"]),
        account_status=AccountStatus.from_value(cast(str, raw_status)),
    )


def _status_to_is_active(status: AccountStatus) -> bool:
    """Translate account status to compatibility boolean flag."""

    return status is AccountStatus.ACTIVE


def _user_columns() -> tuple[sa.Column[Any], ...]:
    """Return reusable user projection used across repository queries."""

    return (
        users.c.id,
        users.c.email,
        users.c.password_hash,
        users.c.role,
        users.c.is_active,
        users.c.account_status,
        users.c.created_at,
        users.c.updated_at,
    )
