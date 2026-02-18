from __future__ import annotations

from pathlib import Path


def test_widget_http_router_and_static_assets_are_removed() -> None:
    router_path = Path("src/triage_automation/infrastructure/http/widget_router.py")
    static_widget_dir = Path("apps/bot_api/static/widget/room2")

    assert not router_path.exists()
    assert not static_widget_dir.exists()
