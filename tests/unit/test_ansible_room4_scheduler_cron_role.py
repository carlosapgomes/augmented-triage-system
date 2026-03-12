"""Tests for Room-4 scheduler cron role structure and task contracts."""

from __future__ import annotations

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_room4_scheduler_cron_role_declares_defaults_and_rootless_cron_tasks() -> None:
    """Ensure cron role declares defaults and manages cron in service-user context."""

    defaults = _read("ansible/roles/room4_scheduler_cron/defaults/main.yml")
    tasks = _read("ansible/roles/room4_scheduler_cron/tasks/main.yml")

    assert "ats_room4_scheduler_cron_job_name:" in defaults
    assert "ats_room4_scheduler_cron_timezone:" in defaults
    assert "ats_room4_scheduler_cron_minute:" in defaults
    assert "ats_room4_scheduler_cron_hour:" in defaults
    assert "ats_room4_scheduler_cron_log_file:" in defaults
    assert 'ats_room4_scheduler_cron_timezone: "UTC"' in defaults
    assert 'ats_room4_scheduler_cron_hour: "10,16,22"' in defaults

    assert "id -u {{ ats_service_user }}" in tasks
    assert "ats_room4_scheduler_cron_state" in tasks
    assert "ansible.builtin.cron:" in tasks
    assert "user: \"{{ ats_service_user }}\"" in tasks
    assert "env: true" in tasks
    assert "name: CRON_TZ" in tasks
    assert "name: XDG_RUNTIME_DIR" in tasks
    assert "name: DOCKER_HOST" in tasks
    assert "run --rm --no-deps worker uv run python -m apps.scheduler.main" in tasks
    assert "{{ ats_room4_scheduler_cron_log_file }} 2>&1" in tasks


def test_room4_scheduler_cron_role_removes_job_when_disabled() -> None:
    """Ensure role supports absent state to remove managed cron entries."""

    tasks = _read("ansible/roles/room4_scheduler_cron/tasks/main.yml")

    assert "'present' if (ats_room4_scheduler_cron_enabled | bool) else 'absent'" in tasks
    assert "state: \"{{ ats_room4_scheduler_cron_state }}\"" in tasks
