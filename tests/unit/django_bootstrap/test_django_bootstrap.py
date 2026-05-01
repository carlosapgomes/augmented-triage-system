"""Tests for Django operations app bootstrap and smoke route.

Validates that the Django app boots correctly, serves HTTP responses,
and is independent from the existing FastAPI runtime.
"""

import os

import django
from django.test import RequestFactory

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "apps.django_ops.settings",
)
if not django.conf.settings.configured:
    django.setup()


class TestDjangoBootstrap:
    """Validate Django app boots with valid settings."""

    def test_django_imports_successfully(self) -> None:
        """Django core must be importable without errors."""
        import django

        assert django.VERSION[0] >= 5

    def test_django_settings_module_is_configured(self) -> None:
        """The DJANGO_SETTINGS_MODULE must point to our ops settings."""
        import django.conf

        assert (
            django.conf.settings.SETTINGS_MODULE
            == "apps.django_ops.settings"
        )

    def test_django_installed_apps_contains_ops(self) -> None:
        """The django_ops app must be in INSTALLED_APPS."""
        from django.conf import settings

        assert "apps.django_ops" in settings.INSTALLED_APPS

    def test_django_debug_is_false(self) -> None:
        """DEBUG must be False in the default settings."""
        from django.conf import settings

        assert settings.DEBUG is False


class TestSmokeRoute:
    """Validate the health/smoke view responds correctly."""

    def test_smoke_view_returns_200(self) -> None:
        """The smoke/health route must respond with HTTP 200."""
        from apps.django_ops.views import smoke

        factory = RequestFactory()
        request = factory.get("/smoke/")
        response = smoke(request)

        assert response.status_code == 200

    def test_smoke_view_returns_json_content_type(self) -> None:
        """The smoke route must return application/json."""
        from apps.django_ops.views import smoke

        factory = RequestFactory()
        request = factory.get("/smoke/")
        response = smoke(request)

        assert response["Content-Type"] == "application/json"

    def test_smoke_view_body_contains_status_ok(self) -> None:
        """The smoke route response body must contain status ok."""
        import json

        from apps.django_ops.views import smoke

        factory = RequestFactory()
        request = factory.get("/smoke/")
        response = smoke(request)
        body = json.loads(response.content)

        assert body["status"] == "ok"


class TestDjangoIndependenceFromFastAPI:
    """Validate Django boot does not depend on FastAPI runtime."""

    def test_django_boots_without_fastapi_import(self) -> None:
        """Django settings must not import or reference FastAPI modules."""
        from django.conf import settings

        settings_str = str(settings.INSTALLED_APPS)
        assert "fastapi" not in settings_str.lower()
        assert "bot_api" not in settings_str

    def test_django_root_urlconf_is_ops(self) -> None:
        """ROOT_URLCONF must point to django_ops, not the FastAPI app."""
        from django.conf import settings

        assert settings.ROOT_URLCONF == "apps.django_ops.urls"
