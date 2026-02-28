from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.config import Config

from alembic import command
from triage_automation.application.ports.supervisor_summary_dispatch_repository_port import (
    SupervisorSummaryDispatchSentInput,
    SupervisorSummaryWindowKey,
)
from triage_automation.infrastructure.db.session import create_session_factory
from triage_automation.infrastructure.db.supervisor_summary_dispatch_repository import (
    SqlAlchemySupervisorSummaryDispatchRepository,
)


def _upgrade_head(tmp_path: Path, filename: str) -> tuple[str, str]:
    db_path = tmp_path / filename
    sync_url = f"sqlite+pysqlite:///{db_path}"
    async_url = f"sqlite+aiosqlite:///{db_path}"

    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(alembic_config, "head")

    return sync_url, async_url


@pytest.mark.asyncio
async def test_claim_window_is_idempotent_for_existing_room_window(tmp_path: Path) -> None:
    _, async_url = _upgrade_head(tmp_path, "summary_dispatch_claim.db")
    session_factory = create_session_factory(async_url)
    repository = SqlAlchemySupervisorSummaryDispatchRepository(session_factory)

    key = SupervisorSummaryWindowKey(
        room_id="!room4:example.org",
        window_start=datetime(2026, 2, 15, 19, 0, tzinfo=UTC),
        window_end=datetime(2026, 2, 16, 7, 0, tzinfo=UTC),
    )

    first_claim = await repository.claim_window(key)
    second_claim = await repository.claim_window(key)
    record = await repository.get_by_window(
        room_id=key.room_id,
        window_start=key.window_start,
        window_end=key.window_end,
    )

    assert first_claim is True
    assert second_claim is False
    assert record is not None
    assert record.status == "pending"


@pytest.mark.asyncio
async def test_mark_sent_is_compare_and_set_for_pending_window(tmp_path: Path) -> None:
    _, async_url = _upgrade_head(tmp_path, "summary_dispatch_mark_sent.db")
    session_factory = create_session_factory(async_url)
    repository = SqlAlchemySupervisorSummaryDispatchRepository(session_factory)

    key = SupervisorSummaryWindowKey(
        room_id="!room4:example.org",
        window_start=datetime(2026, 2, 16, 7, 0, tzinfo=UTC),
        window_end=datetime(2026, 2, 16, 19, 0, tzinfo=UTC),
    )
    await repository.claim_window(key)

    first_mark = await repository.mark_sent(
        SupervisorSummaryDispatchSentInput(
            room_id=key.room_id,
            window_start=key.window_start,
            window_end=key.window_end,
            matrix_event_id="$summary-first",
            sent_at=datetime(2026, 2, 16, 19, 1, tzinfo=UTC),
        )
    )
    second_mark = await repository.mark_sent(
        SupervisorSummaryDispatchSentInput(
            room_id=key.room_id,
            window_start=key.window_start,
            window_end=key.window_end,
            matrix_event_id="$summary-second",
            sent_at=datetime(2026, 2, 16, 19, 2, tzinfo=UTC),
        )
    )
    record = await repository.get_by_window(
        room_id=key.room_id,
        window_start=key.window_start,
        window_end=key.window_end,
    )

    assert first_mark is True
    assert second_mark is False
    assert record is not None
    assert record.status == "sent"
    assert record.matrix_event_id == "$summary-first"


@pytest.mark.asyncio
async def test_claim_window_reclaims_failed_dispatch_by_cas_update(tmp_path: Path) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "summary_dispatch_reclaim_failed.db")
    session_factory = create_session_factory(async_url)
    repository = SqlAlchemySupervisorSummaryDispatchRepository(session_factory)

    key = SupervisorSummaryWindowKey(
        room_id="!room4:example.org",
        window_start=datetime(2026, 2, 15, 19, 0, tzinfo=UTC),
        window_end=datetime(2026, 2, 16, 7, 0, tzinfo=UTC),
    )
    await repository.claim_window(key)

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "UPDATE supervisor_summary_dispatches "
                "SET status = 'failed', last_error = 'transient error' "
                "WHERE room_id = :room_id"
            ),
            {"room_id": key.room_id},
        )

    reclaimed = await repository.claim_window(key)
    record = await repository.get_by_window(
        room_id=key.room_id,
        window_start=key.window_start,
        window_end=key.window_end,
    )

    assert reclaimed is True
    assert record is not None
    assert record.status == "pending"
    assert record.last_error is None
