from __future__ import annotations

import importlib
from datetime import UTC, datetime, timedelta
from typing import Any


def _resolve_previous_summary_window(*, run_at_utc: datetime) -> Any:
    module = importlib.import_module(
        "triage_automation.application.services.supervisor_summary_scheduler_service"
    )
    resolver = getattr(module, "resolve_previous_summary_window")
    return resolver(
        run_at_utc=run_at_utc,
        timezone_name="America/Bahia",
        morning_hour=7,
        evening_hour=19,
    )


def test_morning_cutoff_resolves_previous_night_window_in_utc() -> None:
    run_at_utc = datetime(2026, 2, 16, 10, 0, tzinfo=UTC)

    resolved = _resolve_previous_summary_window(run_at_utc=run_at_utc)

    assert resolved.window_start_utc == datetime(2026, 2, 15, 22, 0, tzinfo=UTC)
    assert resolved.window_end_utc == datetime(2026, 2, 16, 10, 0, tzinfo=UTC)
    assert resolved.window_start_utc < resolved.window_end_utc
    assert resolved.window_end_utc - resolved.window_start_utc == timedelta(hours=12)


def test_evening_cutoff_resolves_same_day_window_in_utc() -> None:
    run_at_utc = datetime(2026, 2, 16, 22, 0, tzinfo=UTC)

    resolved = _resolve_previous_summary_window(run_at_utc=run_at_utc)

    assert resolved.window_start_utc == datetime(2026, 2, 16, 10, 0, tzinfo=UTC)
    assert resolved.window_end_utc == datetime(2026, 2, 16, 22, 0, tzinfo=UTC)
    assert resolved.window_start_utc < resolved.window_end_utc
    assert resolved.window_end_utc - resolved.window_start_utc == timedelta(hours=12)
