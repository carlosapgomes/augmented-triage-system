from __future__ import annotations

import inspect
import logging
from collections.abc import Coroutine
from datetime import UTC, datetime
from typing import Any, cast
from zoneinfo import ZoneInfo

import pytest
from pytest import LogCaptureFixture, MonkeyPatch

from apps.scheduler import main as scheduler_main
from triage_automation.application.services.supervisor_summary_scheduler_service import (
    SupervisorSummaryScheduleResult,
    SupervisorSummaryWindow,
)
from triage_automation.config.settings import Settings


def test_main_runs_one_shot_scheduler_via_asyncio(monkeypatch: MonkeyPatch) -> None:
    captured: dict[str, bool] = {}

    def _fake_run(coro: object) -> None:
        captured["is_coroutine"] = inspect.iscoroutine(coro)
        assert inspect.iscoroutine(coro)
        cast(Coroutine[Any, Any, Any], coro).close()

    monkeypatch.setattr("apps.scheduler.main.asyncio.run", _fake_run)

    scheduler_main.main()

    assert captured["is_coroutine"] is True


class _SchedulerServiceStub:
    def __init__(self, result: SupervisorSummaryScheduleResult) -> None:
        self._result = result
        self.calls: list[datetime | None] = []

    async def enqueue_previous_window_summary(
        self,
        *,
        run_at_utc: datetime | None = None,
    ) -> SupervisorSummaryScheduleResult:
        self.calls.append(run_at_utc)
        return self._result


@pytest.mark.asyncio
async def test_run_scheduler_once_logs_window_observability_fields(
    monkeypatch: MonkeyPatch,
    caplog: LogCaptureFixture,
) -> None:
    monkeypatch.setattr("apps.scheduler.main.configure_logging", lambda level: None)

    result = SupervisorSummaryScheduleResult(
        claimed_dispatch=True,
        enqueued_job_id=99,
        window=SupervisorSummaryWindow(
            window_start_local=datetime(
                2026,
                2,
                16,
                13,
                0,
                tzinfo=ZoneInfo("America/Bahia"),
            ),
            window_end_local=datetime(
                2026,
                2,
                16,
                19,
                0,
                tzinfo=ZoneInfo("America/Bahia"),
            ),
            window_start_utc=datetime(2026, 2, 16, 16, 0, tzinfo=UTC),
            window_end_utc=datetime(2026, 2, 16, 22, 0, tzinfo=UTC),
        ),
    )
    scheduler_service = _SchedulerServiceStub(result)
    settings = Settings.model_construct(
        room4_id="!room4:example.org",
        supervisor_summary_timezone="America/Bahia",
        log_level="INFO",
    )
    run_at_utc = datetime(2026, 2, 16, 22, 0, tzinfo=UTC)

    logger_name = "apps.scheduler.main"
    caplog.set_level(logging.INFO, logger=logger_name)

    await scheduler_main.run_scheduler_once(
        settings=settings,
        scheduler_service=cast(Any, scheduler_service),
        run_at_utc=run_at_utc,
    )

    assert scheduler_service.calls == [run_at_utc]
    messages = [record.getMessage() for record in caplog.records if record.name == logger_name]
    assert any("window_start_utc=2026-02-16T16:00:00+00:00" in message for message in messages)
    assert any("window_end_utc=2026-02-16T22:00:00+00:00" in message for message in messages)
    assert any("timezone=America/Bahia" in message for message in messages)
    assert any("cutoff_hour_local=19" in message for message in messages)
    assert any("catch_up_enabled=False" in message for message in messages)
