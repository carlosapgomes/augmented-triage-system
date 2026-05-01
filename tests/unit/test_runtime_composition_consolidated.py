"""Tests for consolidated runtime composition including the Django web app.

These tests verify that the supported runtime composition includes the Django
web application alongside the existing services, and that local/compose startup
paths remain coherent.
"""

from __future__ import annotations

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_local_compose_includes_django_ops_service() -> None:
    """Ensure local docker-compose.yml includes django-ops service."""
    content = _read("docker-compose.yml")

    assert "services:" in content
    assert "django-ops:" in content, (
        "Consolidated runtime composition must include django-ops service"
    )
    assert "build:" in content
    assert "django_ops" in content or "django-ops" in content
    assert "depends_on:" in content
    assert "postgres" in content


def test_local_compose_retains_existing_services() -> None:
    """Ensure local compose still has bot-api, bot-matrix, worker, postgres."""
    content = _read("docker-compose.yml")
    # Verify all existing services still present
    for expected in ("postgres:", "bot-api:", "bot-matrix:", "worker:"):
        assert expected in content, f"Service {expected} must remain in compose"


def test_ansible_deploy_defaults_include_django_ops_service() -> None:
    """Ensure Ansible deploy defaults list django-ops as a deployable service."""
    defaults = _read("ansible/roles/deploy/defaults/main.yml")

    assert "django-ops" in defaults, (
        "ats_runtime_deploy_services must include django-ops"
    )


def test_ansible_deploy_defaults_declare_django_ops_supported_command() -> None:
    """Ensure Ansible deploy defaults declare the supported django-ops command."""
    defaults = _read("ansible/roles/deploy/defaults/main.yml")

    assert "django_ops:" in defaults, (
        "ats_runtime_supported_service_commands must include django_ops entry"
    )
    # Verify it references the Django WSGI/ASGI entrypoint
    assert "apps.django_ops" in defaults


def test_ansible_rootless_compose_template_includes_django_ops() -> None:
    """Ensure the rootless compose template includes the django-ops service."""
    template = _read(
        "ansible/roles/app_runtime/templates/docker-compose.rootless.yml.j2"
    )

    assert "django-ops:" in template, (
        "Rootless compose template must include django-ops service definition"
    )
    assert "{{ ats_runtime_services.django_ops.command | to_json }}" in template


def test_ansible_deploy_tasks_validate_django_ops_command() -> None:
    """Ensure deploy role validates django-ops command against supported composition."""
    tasks = _read("ansible/roles/deploy/tasks/main.yml")

    assert "ats_runtime_services.django_ops.command ==" in tasks
    assert "ats_runtime_supported_service_commands.django_ops" in tasks


def test_runtime_smoke_doc_documents_django_ops_startup() -> None:
    """Ensure runtime-smoke runbook documents the Django web app startup."""
    smoke = _read("docs/runtime-smoke.md")

    assert "django_ops" in smoke or "django-ops" in smoke or "Django" in smoke


def test_architecture_doc_describes_django_ops_in_overview() -> None:
    """Ensure architecture doc lists the Django web app in the overview."""
    architecture = _read("docs/architecture.md")

    assert "django" in architecture.lower() or "Django" in architecture


def test_setup_doc_documents_django_ops_local_startup() -> None:
    """Ensure setup guide documents starting the Django web app locally."""
    setup = _read("docs/setup.md")

    # Should mention the Django app in startup flow
    assert "django" in setup.lower() or "Django" in setup


def test_post_deploy_checks_expect_django_ops() -> None:
    """Ensure post-deploy checks inherit django-ops from deploy services."""
    defaults = _read("ansible/roles/post_deploy_checks/defaults/main.yml")
    deploy_defaults = _read("ansible/roles/deploy/defaults/main.yml")

    # Post-deploy checks reference deploy services dynamically
    assert "ats_post_deploy_expected_services" in defaults
    assert "ats_runtime_deploy_services" in defaults

    # And deploy services itself includes django-ops
    assert "django-ops" in deploy_defaults
