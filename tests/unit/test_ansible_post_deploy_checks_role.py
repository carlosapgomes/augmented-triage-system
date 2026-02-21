"""Tests for post-deploy checks role coverage."""

from __future__ import annotations

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_post_deploy_checks_role_declares_process_logs_and_health_checks() -> None:
    """Ensure post_deploy_checks role validates running services, logs, and HTTP health."""

    defaults = _read("ansible/roles/post_deploy_checks/defaults/main.yml")
    tasks = _read("ansible/roles/post_deploy_checks/tasks/main.yml")
    running_services_guard = (
        "ats_post_deploy_expected_services | "
        "difference(ats_post_deploy_running_services.stdout_lines) | length == 0"
    )

    assert "ats_post_deploy_expected_services:" in defaults
    assert "ats_post_deploy_logs_tail_lines:" in defaults
    assert "ats_post_deploy_log_error_patterns:" in defaults
    assert "ats_post_deploy_bot_api_healthcheck_url:" in defaults
    assert "ats_post_deploy_bot_api_expected_status:" in defaults
    assert "ats_post_deploy_require_services_running_criterion:" in defaults
    assert "ats_post_deploy_require_logs_clean_criterion:" in defaults
    assert "ats_post_deploy_require_bot_api_health_criterion:" in defaults
    assert "ats_post_deploy_require_non_root_runtime_criterion:" in defaults

    assert "id -u {{ ats_service_user }}" in tasks
    assert "docker compose" in tasks
    assert "ps --services --filter status=running" in tasks
    assert running_services_guard in tasks
    assert "docker compose" in tasks
    assert "logs --no-color --tail {{ ats_post_deploy_logs_tail_lines }}" in tasks
    assert "ats_post_deploy_log_error_patterns" in tasks
    assert "ansible.builtin.uri:" in tasks
    assert "url: \"{{ ats_post_deploy_bot_api_healthcheck_url }}\"" in tasks
    assert "ps -q {{ item }}" in tasks
    assert "docker inspect --format '{{.State.Pid}}'" in tasks
    assert "ps -o user= -p" in tasks
    assert "ats_post_deploy_criterion_non_root_runtime" in tasks
    assert "ats_post_deploy_approval_criteria" in tasks
    assert "Validate objective post-deploy approval criteria" in tasks
    assert "Deploy approval gate failed." in tasks
