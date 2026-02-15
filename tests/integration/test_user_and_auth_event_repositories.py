from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic.config import Config

from alembic import command
from triage_automation.application.ports.auth_event_repository_port import (
    AuthEventCreateInput,
)
from triage_automation.application.ports.auth_token_repository_port import (
    AuthTokenCreateInput,
)
from triage_automation.domain.auth.roles import Role
from triage_automation.infrastructure.db.auth_event_repository import SqlAlchemyAuthEventRepository
from triage_automation.infrastructure.db.auth_token_repository import SqlAlchemyAuthTokenRepository
from triage_automation.infrastructure.db.session import create_session_factory
from triage_automation.infrastructure.db.user_repository import SqlAlchemyUserRepository


def _upgrade_head(tmp_path: Path, filename: str) -> tuple[str, str]:
    db_path = tmp_path / filename
    sync_url = f"sqlite+pysqlite:///{db_path}"
    async_url = f"sqlite+aiosqlite:///{db_path}"

    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(alembic_config, "head")

    return sync_url, async_url


def _insert_user(
    connection: sa.Connection,
    *,
    user_id: UUID,
    email: str,
    role: str,
    is_active: bool,
) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO users (id, email, password_hash, role, is_active) "
            "VALUES (:id, :email, :password_hash, :role, :is_active)"
        ),
        {
            "id": user_id.hex,
            "email": email,
            "password_hash": "hash",
            "role": role,
            "is_active": is_active,
        },
    )


def test_role_enum_values_are_exact_admin_and_reader() -> None:
    assert {member.value for member in Role} == {"admin", "reader"}


@pytest.mark.asyncio
async def test_user_repository_fetches_only_active_user_by_email(tmp_path: Path) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "user_repo_active.db")
    session_factory = create_session_factory(async_url)
    repo = SqlAlchemyUserRepository(session_factory)

    engine = sa.create_engine(sync_url)
    active_id = uuid4()
    inactive_id = uuid4()
    with engine.begin() as connection:
        _insert_user(
            connection,
            user_id=active_id,
            email="admin@example.org",
            role="admin",
            is_active=True,
        )
        _insert_user(
            connection,
            user_id=inactive_id,
            email="reader@example.org",
            role="reader",
            is_active=False,
        )

    active_user = await repo.get_active_by_email(email="admin@example.org")
    inactive_user = await repo.get_active_by_email(email="reader@example.org")

    assert active_user is not None
    assert active_user.user_id == active_id
    assert active_user.email == "admin@example.org"
    assert active_user.role == Role.ADMIN
    assert inactive_user is None


@pytest.mark.asyncio
async def test_auth_event_repository_appends_events(tmp_path: Path) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "auth_event_repo.db")
    session_factory = create_session_factory(async_url)
    user_repo = SqlAlchemyUserRepository(session_factory)
    auth_event_repo = SqlAlchemyAuthEventRepository(session_factory)

    engine = sa.create_engine(sync_url)
    user_id = uuid4()
    with engine.begin() as connection:
        _insert_user(
            connection,
            user_id=user_id,
            email="reader@example.org",
            role="reader",
            is_active=True,
        )

    inserted = await auth_event_repo.append_event(
        AuthEventCreateInput(
            user_id=user_id,
            event_type="LOGIN_SUCCESS",
            ip_address="127.0.0.1",
            user_agent="pytest",
            payload={"source": "integration-test"},
        )
    )
    assert inserted > 0

    fetched = await user_repo.get_active_by_email(email="reader@example.org")
    assert fetched is not None
    assert fetched.user_id == user_id

    with engine.begin() as connection:
        row = connection.execute(
            sa.text(
                "SELECT event_type, ip_address, user_agent, payload "
                "FROM auth_events WHERE id = :id"
            ),
            {"id": inserted},
        ).mappings().one()

    assert row["event_type"] == "LOGIN_SUCCESS"
    assert row["ip_address"] == "127.0.0.1"
    assert row["user_agent"] == "pytest"
    assert "integration-test" in str(row["payload"])


@pytest.mark.asyncio
async def test_auth_token_repository_persists_and_resolves_active_tokens(tmp_path: Path) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "auth_token_repo.db")
    session_factory = create_session_factory(async_url)
    token_repo = SqlAlchemyAuthTokenRepository(session_factory)

    engine = sa.create_engine(sync_url)
    user_id = uuid4()
    with engine.begin() as connection:
        _insert_user(
            connection,
            user_id=user_id,
            email="admin@example.org",
            role="admin",
            is_active=True,
        )

    expires_at = datetime.now(tz=UTC) + timedelta(hours=1)
    token = await token_repo.create_token(
        AuthTokenCreateInput(
            user_id=user_id,
            token_hash="opaque-token-hash",
            expires_at=expires_at,
        )
    )
    assert token.token_hash == "opaque-token-hash"

    active = await token_repo.get_active_by_hash(token_hash="opaque-token-hash")
    assert active is not None
    assert active.user_id == user_id

    with engine.begin() as connection:
        connection.execute(
            sa.text("UPDATE auth_tokens SET revoked_at = CURRENT_TIMESTAMP WHERE id = :id"),
            {"id": token.id},
        )

    revoked = await token_repo.get_active_by_hash(token_hash="opaque-token-hash")
    assert revoked is None
