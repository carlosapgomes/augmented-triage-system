from __future__ import annotations

import inspect
from collections.abc import Coroutine
from typing import Any, cast

from pytest import MonkeyPatch

from apps.scheduler import main as scheduler_main


def test_main_runs_one_shot_scheduler_via_asyncio(monkeypatch: MonkeyPatch) -> None:
    captured: dict[str, bool] = {}

    def _fake_run(coro: object) -> None:
        captured["is_coroutine"] = inspect.iscoroutine(coro)
        assert inspect.iscoroutine(coro)
        cast(Coroutine[Any, Any, Any], coro).close()

    monkeypatch.setattr("apps.scheduler.main.asyncio.run", _fake_run)

    scheduler_main.main()

    assert captured["is_coroutine"] is True
