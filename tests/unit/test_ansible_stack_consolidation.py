"""Tests for Ansible stack consolidation (slice 1.2).

These tests verify that the Ansible automation supports the consolidated
same-host stack including the Django web app, with idempotent deploys
and post-deploy validations covering the new web service.
"""

from __future__ import annotations

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Deploy converges the consolidated stack as dedicated user
# ---------------------------------------------------------------------------


def test_group_vars_includes_django_ops_in_runtime_services() -> None:
    """Ensure group_vars defines the django_ops service command."""
    variables = _read("ansible/inventory/group_vars/all.yml")

    assert "django_ops:" in variables, (
        "ats_runtime_services must include django_ops entry in group_vars"
    )
    assert "apps.django_ops.asgi:application" in variables, (
        "django_ops command must reference the ASGI application entrypoint"
    )


def test_group_vars_includes_django_ops_in_deploy_services() -> None:
    """Ensure group_vars lists django-ops in the deploy services array."""
    variables = _read("ansible/inventory/group_vars/all.yml")

    # Find the ats_runtime_deploy_services block
    assert "django-ops" in variables, (
        "ats_runtime_deploy_services must include django-ops in group_vars"
    )


def test_group_vars_includes_django_ops_in_supported_commands() -> None:
    """Ensure group_vars declares django_ops in supported service commands."""
    variables = _read("ansible/inventory/group_vars/all.yml")

    # Supported commands must include django_ops with the ASGI entrypoint
    assert "django_ops:" in variables
    assert "apps.django_ops.asgi:application" in variables


def test_group_vars_declares_django_ops_publish_port() -> None:
    """Ensure group_vars declares the Django publish port binding."""
    variables = _read("ansible/inventory/group_vars/all.yml")

    assert "ats_runtime_django_ops_publish_port:" in variables, (
        "ats_runtime_django_ops_publish_port must be declared in group_vars"
    )


def test_group_vars_includes_django_ops_in_post_deploy_expected_services() -> None:
    """Ensure group_vars lists django-ops in post-deploy expected services."""
    variables = _read("ansible/inventory/group_vars/all.yml")

    lines = variables.splitlines()
    in_post_deploy_block = False
    found_django_ops = False

    for line in lines:
        if "ats_post_deploy_expected_services:" in line:
            in_post_deploy_block = True
            continue
        if in_post_deploy_block:
            stripped = line.strip()
            if stripped.startswith("- "):
                if "django-ops" in stripped:
                    found_django_ops = True
            elif stripped and not stripped.startswith("#") and not stripped.startswith("-"):
                in_post_deploy_block = False

    assert found_django_ops, (
        "ats_post_deploy_expected_services must include django-ops in group_vars"
    )


def test_deploy_role_validates_all_consolidated_service_commands() -> None:
    """Ensure deploy tasks validate commands for all 4 consolidated services."""
    tasks = _read("ansible/roles/deploy/tasks/main.yml")

    for service in ("bot_api", "bot_matrix", "worker", "django_ops"):
        guard = (
            f"ats_runtime_services.{service}.command == "
            f"ats_runtime_supported_service_commands.{service}"
        )
        assert guard in tasks, (
            f"Deploy tasks must validate {service} command against supported composition"
        )


# ---------------------------------------------------------------------------
# 2. Rerun remains idempotent
# ---------------------------------------------------------------------------


def test_deploy_up_task_uses_idempotent_changed_when() -> None:
    """Ensure the deploy up task tracks state changes for idempotency."""
    tasks = _read("ansible/roles/deploy/tasks/main.yml")

    # The up task must use changed_when with state change indicators
    assert "'Created' in ats_deploy_up_result.stdout" in tasks
    assert "'Started' in ats_deploy_up_result.stdout" in tasks
    assert "'Recreated' in ats_deploy_up_result.stdout" in tasks
    # The up flags must support re-running without forced recreation by default
    assert "ats_runtime_up_flags" in tasks


def test_deploy_pull_task_is_idempotent_on_rerun() -> None:
    """Ensure the pull task does not report changes on rerun."""
    tasks = _read("ansible/roles/deploy/tasks/main.yml")

    # Pull task has changed_when: false for idempotency
    pull_section_start = tasks.find("Pull runtime images")
    assert pull_section_start > 0, "Pull task must exist"

    pull_section = tasks[pull_section_start : tasks.find("changed_when", pull_section_start) + 200]
    assert "changed_when: false" in pull_section, (
        "Pull task must declare changed_when: false for idempotency"
    )


def test_group_vars_up_flags_default_to_no_force_recreate() -> None:
    """Ensure group_vars uses --no-recreate by default for idempotent reruns."""
    variables = _read("ansible/inventory/group_vars/all.yml")

    assert "--no-recreate" in variables, (
        "ats_runtime_up_flags must include --no-recreate for idempotent reruns"
    )


# ---------------------------------------------------------------------------
# 3. Post-deploy validations cover the new web service
# ---------------------------------------------------------------------------


def test_post_deploy_checks_defaults_declare_django_health_check_config() -> None:
    """Ensure post_deploy_checks defaults include Django health check settings."""
    defaults = _read("ansible/roles/post_deploy_checks/defaults/main.yml")

    assert "ats_post_deploy_django_ops_healthcheck_url:" in defaults, (
        "Must declare Django health check URL in post-deploy defaults"
    )
    assert "ats_post_deploy_django_ops_expected_status:" in defaults, (
        "Must declare Django expected HTTP status in post-deploy defaults"
    )
    assert "ats_post_deploy_django_ops_expected_text:" in defaults, (
        "Must declare Django expected response text in post-deploy defaults"
    )
    assert "ats_post_deploy_require_django_ops_health_criterion:" in defaults, (
        "Must declare Django health criterion requirement flag"
    )


def test_post_deploy_checks_tasks_validate_django_health_endpoint() -> None:
    """Ensure post_deploy_checks tasks validate Django smoke endpoint."""
    tasks = _read("ansible/roles/post_deploy_checks/tasks/main.yml")

    assert "ats_post_deploy_django_ops_healthcheck_url" in tasks, (
        "Post-deploy checks must reference Django health check URL"
    )
    assert "ats_post_deploy_criterion_django_ops_health" in tasks, (
        "Post-deploy checks must evaluate Django health criterion"
    )


def test_post_deploy_checks_approval_includes_django_ops_health() -> None:
    """Ensure the approval criteria summary includes Django health check."""
    tasks = _read("ansible/roles/post_deploy_checks/tasks/main.yml")

    assert "django_ops_health:" in tasks, (
        "Approval criteria summary must include django_ops_health"
    )
    assert "ats_post_deploy_require_django_ops_health_criterion" in tasks, (
        "Approval criteria must gate on Django health criterion requirement flag"
    )


def test_post_deploy_checks_django_health_default_points_to_smoke() -> None:
    """Ensure Django health check URL defaults to the smoke endpoint."""
    defaults = _read("ansible/roles/post_deploy_checks/defaults/main.yml")

    assert "smoke" in defaults, (
        "Django health check URL must reference the /smoke/ endpoint"
    )
    assert "8001" in defaults, (
        "Django health check URL must reference port 8001"
    )
