"""Tests for service-user role structure and bootstrap wiring."""

from __future__ import annotations

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_service_user_role_declares_group_and_user_management_tasks() -> None:
    """Ensure service_user role manages dedicated group and user account."""

    defaults = _read("ansible/roles/service_user/defaults/main.yml")
    tasks = _read("ansible/roles/service_user/tasks/main.yml")

    assert "ats_service_user_shell:" in defaults
    assert "ats_service_user_system:" in defaults

    assert "ansible.builtin.group:" in tasks
    assert "name: \"{{ ats_service_group }}\"" in tasks
    assert "ansible.builtin.user:" in tasks
    assert "name: \"{{ ats_service_user }}\"" in tasks
    assert "group: \"{{ ats_service_group }}\"" in tasks
    assert "home: \"{{ ats_service_home }}\"" in tasks
    assert "create_home: true" in tasks


def test_bootstrap_playbook_invokes_service_user_role() -> None:
    """Ensure bootstrap playbook wires the service_user role."""

    bootstrap = _read("ansible/playbooks/bootstrap.yml")

    assert "name: service_user" in bootstrap
