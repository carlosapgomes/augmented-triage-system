from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.config import Config

from alembic import command
from triage_automation.application.ports.job_queue_port import JobEnqueueInput
from triage_automation.application.services.backoff import compute_retry_delay
from triage_automation.infrastructure.db.job_queue_repository import SqlAlchemyJobQueueRepository
from triage_automation.infrastructure.db.session import create_session_factory


def _upgrade_head(tmp_path: Path, filename: str) -> tuple[str, str]:
    db_path = tmp_path / filename
    sync_url = f"sqlite+pysqlite:///{db_path}"
    async_url = f"sqlite+aiosqlite:///{db_path}"

    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(alembic_config, "head")

    return sync_url, async_url


async def _enqueue_batch(repo: SqlAlchemyJobQueueRepository, count: int) -> list[int]:
    created_ids: list[int] = []
    for index in range(count):
        record = await repo.enqueue(JobEnqueueInput(job_type=f"job-{index}"))
        created_ids.append(record.job_id)
    return created_ids


async def _claim_one(repo: SqlAlchemyJobQueueRepository) -> list[int]:
    claimed = await repo.claim_due_jobs(limit=1)
    return [job.job_id for job in claimed]


async def _load_job_status(sync_url: str, job_id: int) -> str:
    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        status = connection.execute(
            sa.text("SELECT status FROM jobs WHERE job_id = :job_id"),
            {"job_id": job_id},
        ).scalar_one()
    return str(status)


async def _load_job_attempts(sync_url: str, job_id: int) -> int:
    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        attempts = connection.execute(
            sa.text("SELECT attempts FROM jobs WHERE job_id = :job_id"),
            {"job_id": job_id},
        ).scalar_one()
    return int(attempts)


async def _load_job_run_after(sync_url: str, job_id: int) -> datetime:
    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        run_after = connection.execute(
            sa.text("SELECT run_after FROM jobs WHERE job_id = :job_id"),
            {"job_id": job_id},
        ).scalar_one()

    if isinstance(run_after, str):
        return datetime.fromisoformat(run_after).replace(tzinfo=UTC)
    return run_after


async def _load_job_last_error(sync_url: str, job_id: int) -> str | None:
    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        value = connection.execute(
            sa.text("SELECT last_error FROM jobs WHERE job_id = :job_id"),
            {"job_id": job_id},
        ).scalar_one_or_none()
    return value


async def _load_job_payload(sync_url: str, job_id: int) -> str:
    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        payload = connection.execute(
            sa.text("SELECT payload FROM jobs WHERE job_id = :job_id"),
            {"job_id": job_id},
        ).scalar_one()
    return str(payload)


@pytest.mark.asyncio
async def test_enqueue_creates_queued_job(tmp_path: Path) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "enqueue.db")
    session_factory = create_session_factory(async_url)
    repo = SqlAlchemyJobQueueRepository(session_factory)

    record = await repo.enqueue(
        JobEnqueueInput(
            job_type="process_pdf_case",
            payload={"key": "value"},
            max_attempts=7,
        )
    )

    assert record.status == "queued"
    assert record.job_type == "process_pdf_case"
    assert record.max_attempts == 7
    assert record.attempts == 0
    assert await _load_job_status(sync_url, record.job_id) == "queued"
    assert "key" in await _load_job_payload(sync_url, record.job_id)


@pytest.mark.asyncio
async def test_concurrent_claims_get_distinct_jobs(tmp_path: Path) -> None:
    _, async_url = _upgrade_head(tmp_path, "concurrent_claim.db")
    session_factory = create_session_factory(async_url)
    repo_one = SqlAlchemyJobQueueRepository(session_factory)
    repo_two = SqlAlchemyJobQueueRepository(session_factory)

    await _enqueue_batch(repo_one, 2)

    claimed_one, claimed_two = await asyncio.gather(_claim_one(repo_one), _claim_one(repo_two))

    assert len(claimed_one) == 1
    assert len(claimed_two) == 1
    assert claimed_one[0] != claimed_two[0]


@pytest.mark.asyncio
async def test_run_after_scheduling_is_respected(tmp_path: Path) -> None:
    _, async_url = _upgrade_head(tmp_path, "run_after.db")
    session_factory = create_session_factory(async_url)
    repo = SqlAlchemyJobQueueRepository(session_factory)

    future_time = datetime.now(tz=UTC) + timedelta(hours=1)
    await repo.enqueue(JobEnqueueInput(job_type="future-job", run_after=future_time))

    claimed = await repo.claim_due_jobs(limit=10)

    assert claimed == []


@pytest.mark.asyncio
async def test_schedule_retry_updates_attempts_and_run_after(tmp_path: Path) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "retry.db")
    session_factory = create_session_factory(async_url)
    repo = SqlAlchemyJobQueueRepository(session_factory)

    created = await repo.enqueue(JobEnqueueInput(job_type="retryable"))
    delay = compute_retry_delay(1)
    next_run = datetime.now(tz=UTC) + delay

    retried = await repo.schedule_retry(
        job_id=created.job_id,
        run_after=next_run,
        last_error="temporary failure",
    )

    assert retried.status == "queued"
    assert retried.attempts == 1
    persisted_attempts = await _load_job_attempts(sync_url, created.job_id)
    assert persisted_attempts == 1

    persisted_run_after = await _load_job_run_after(sync_url, created.job_id)
    assert persisted_run_after >= datetime.now(tz=UTC)


@pytest.mark.asyncio
async def test_mark_dead_sets_dead_status(tmp_path: Path) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "dead.db")
    session_factory = create_session_factory(async_url)
    repo = SqlAlchemyJobQueueRepository(session_factory)

    created = await repo.enqueue(JobEnqueueInput(job_type="dead-letter"))

    dead = await repo.mark_dead(job_id=created.job_id, last_error="max attempts reached")

    assert dead.status == "dead"
    assert dead.last_error == "max attempts reached"
    assert await _load_job_status(sync_url, created.job_id) == "dead"
    assert await _load_job_last_error(sync_url, created.job_id) == "max attempts reached"
