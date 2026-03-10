from __future__ import annotations

from pathlib import Path


def _read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_pwa_base_icon_art_uses_square_chd_dashboard_composition() -> None:
    icon_path = Path("src/triage_automation/infrastructure/http/static/pwa/icons/chd-base.svg")

    assert icon_path.exists()
    icon_svg = _read_text(str(icon_path))
    assert "viewBox=\"0 0 512 512\"" in icon_svg
    assert ">CHD<" in icon_svg
    assert ">dashboard<" in icon_svg
    assert "#0b4263" in icon_svg
    assert "#1b5f78" in icon_svg
    assert "#2f8f9d" in icon_svg
