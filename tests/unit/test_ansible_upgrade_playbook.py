"""Tests for upgrade playbook wiring and post-deploy validation."""

from __future__ import annotations

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_upgrade_playbook_declares_versioned_upgrade_and_post_deploy_checks() -> None:
    """Ensure upgrade playbook performs deploy and validates running services."""

    playbook = _read("ansible/playbooks/upgrade.yml")
    explicit_tag_guard = (
        "ats_runtime_allow_latest_tag or "
        '(ats_runtime_image_tag | lower != "latest")'
    )
    running_services_guard = (
        "ats_runtime_deploy_services | "
        "difference(ats_upgrade_running_services.stdout_lines) | length == 0"
    )

    assert "name: Upgrade ATS runtime services" in playbook
    assert "pre_tasks:" in playbook
    assert "Validate explicit deploy image tag" in playbook
    assert explicit_tag_guard in playbook
    assert "name: app_runtime" in playbook
    assert "name: deploy" in playbook
    assert "post_tasks:" in playbook
    assert "docker compose" in playbook
    assert "ps --services --filter status=running" in playbook
    assert "register: ats_upgrade_running_services" in playbook
    assert running_services_guard in playbook
    assert "Post-deploy validation failed" in playbook
