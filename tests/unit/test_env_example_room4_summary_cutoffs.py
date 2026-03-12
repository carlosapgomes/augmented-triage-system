"""Tests for Room-4 summary cutoff defaults declared in .env.example."""

from __future__ import annotations

from pathlib import Path


def test_env_example_uses_cutoff_hours_contract_for_room4_summary() -> None:
    """Ensure .env.example declares new cutoff list env and removes legacy hour vars."""

    env_example = Path(".env.example").read_text(encoding="utf-8")

    assert "SUPERVISOR_SUMMARY_TIMEZONE=America/Bahia" in env_example
    assert "SUPERVISOR_SUMMARY_CUTOFF_HOURS=7,13,19" in env_example
    assert "SUPERVISOR_SUMMARY_MORNING_HOUR" not in env_example
    assert "SUPERVISOR_SUMMARY_EVENING_HOUR" not in env_example
