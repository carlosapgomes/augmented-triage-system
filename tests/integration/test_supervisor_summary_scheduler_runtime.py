from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.config import Config

from alembic import command
from apps.scheduler.main import run_scheduler_once
from triage_automation.config.settings import Settings


def _upgrade_head(tmp_path: Path, filename: str) -> str:
    db_path = tmp_path / filename
    sync_url = f"sqlite+pysqlite:///{db_path}"

    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(alembic_config, "head")

    return sync_url


def _runtime_settings(*, database_url: str) -> Settings:
    return Settings.model_construct(
        room1_id="!room1:example.org",
        room2_id="!room2:example.org",
        room3_id="!room3:example.org",
        room4_id="!room4:example.org",
        matrix_homeserver_url="https://matrix.example.org",
        matrix_bot_user_id="@bot:example.org",
        matrix_access_token="matrix-token",
        matrix_sync_timeout_ms=30_000,
        matrix_poll_interval_seconds=0.0,
        worker_poll_interval_seconds=0.0,
        supervisor_summary_timezone="America/Bahia",
        supervisor_summary_morning_hour=7,
        supervisor_summary_evening_hour=19,
        webhook_public_url="https://webhook.example.org",
        widget_public_url="https://webhook.example.org",
        database_url=database_url,
        webhook_hmac_secret="secret",
        llm_runtime_mode="deterministic",
        openai_api_key=None,
        openai_model_llm1="gpt-4o-mini",
        openai_model_llm2="gpt-4o-mini",
        log_level="INFO",
    )


@pytest.mark.asyncio
async def test_manual_scheduler_rerun_for_same_window_is_idempotent(tmp_path: Path) -> None:
    sync_url = _upgrade_head(tmp_path, "supervisor_summary_scheduler_runtime.db")
    settings = _runtime_settings(database_url=sync_url.replace("pysqlite", "aiosqlite"))
    run_at_utc = datetime(2026, 2, 16, 22, 0, tzinfo=UTC)

    first = await run_scheduler_once(settings=settings, run_at_utc=run_at_utc)
    second = await run_scheduler_once(settings=settings, run_at_utc=run_at_utc)

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        queued_jobs = connection.execute(
            sa.text("SELECT COUNT(*) FROM jobs WHERE job_type = 'post_room4_summary'"),
        ).scalar_one()
        dispatch_rows = connection.execute(
            sa.text("SELECT COUNT(*) FROM supervisor_summary_dispatches"),
        ).scalar_one()

    assert first.claimed_dispatch is True
    assert first.enqueued_job_id is not None
    assert second.claimed_dispatch is False
    assert second.enqueued_job_id is None
    assert int(queued_jobs) == 1
    assert int(dispatch_rows) == 1
