"""Tests for the Django PWA shell (online-only, installable for remote roles).

TDD tests for slice 4.1 — validates that:
- Authenticated pages for remote-capable roles include PWA installability metadata.
- Authenticated pages for intranet-only roles do NOT include PWA metadata.
- The manifest endpoint returns a valid manifest with standalone display.
- The service worker does not serve cached clinical content offline.
- The installed PWA preserves role-aware entry with an active session.
"""

import os
import tempfile
from pathlib import Path

from alembic.config import Config
from django.contrib.auth import get_user_model
from django.test import TestCase

from alembic import command

User = get_user_model()

REMOTE_CAPABLE_ROLES: list[str] = ["doctor", "manager", "admin"]
INTRANET_ONLY_ROLES: list[str] = ["nir", "scheduler"]


class TestPWAManifestEndpoint(TestCase):  # type: ignore[misc]  # untyped Django base
    """Validate the PWA manifest resource endpoint."""

    def test_manifest_returns_200(self) -> None:
        """GET /manifest.webmanifest must return HTTP 200."""
        response = self.client.get("/manifest.webmanifest")
        assert response.status_code == 200

    def test_manifest_content_type_is_manifest_json(self) -> None:
        """Manifest must be served with application/manifest+json content type."""
        response = self.client.get("/manifest.webmanifest")
        assert response["Content-Type"] == "application/manifest+json"

    def test_manifest_is_valid_json(self) -> None:
        """Manifest response body must be valid JSON."""
        import json

        response = self.client.get("/manifest.webmanifest")
        data = json.loads(response.content)
        assert isinstance(data, dict)

    def test_manifest_has_name_and_short_name(self) -> None:
        """Manifest must include name and short_name fields."""
        import json

        response = self.client.get("/manifest.webmanifest")
        data = json.loads(response.content)
        assert "name" in data
        assert "short_name" in data
        assert isinstance(data["name"], str)
        assert isinstance(data["short_name"], str)
        assert len(data["name"]) > 0
        assert len(data["short_name"]) > 0

    def test_manifest_display_is_standalone(self) -> None:
        """Manifest must specify standalone display behavior."""
        import json

        response = self.client.get("/manifest.webmanifest")
        data = json.loads(response.content)
        assert data.get("display") == "standalone"

    def test_manifest_has_start_url(self) -> None:
        """Manifest must have a start_url pointing to the app root."""
        import json

        response = self.client.get("/manifest.webmanifest")
        data = json.loads(response.content)
        assert "start_url" in data
        assert data["start_url"] == "/"

    def test_manifest_has_scope(self) -> None:
        """Manifest must have a scope field."""
        import json

        response = self.client.get("/manifest.webmanifest")
        data = json.loads(response.content)
        assert "scope" in data
        assert data["scope"] == "/"

    def test_manifest_has_theme_and_background_color(self) -> None:
        """Manifest must define theme_color and background_color."""
        import json

        response = self.client.get("/manifest.webmanifest")
        data = json.loads(response.content)
        assert "theme_color" in data
        assert "background_color" in data
        assert data["theme_color"].startswith("#")
        assert data["background_color"].startswith("#")

    def test_manifest_has_icons(self) -> None:
        """Manifest must list at least one icon."""
        import json

        response = self.client.get("/manifest.webmanifest")
        data = json.loads(response.content)
        assert "icons" in data
        assert isinstance(data["icons"], list)
        assert len(data["icons"]) > 0

    def test_manifest_icons_have_required_fields(self) -> None:
        """Each manifest icon entry must have src, sizes, and type."""
        import json

        response = self.client.get("/manifest.webmanifest")
        data = json.loads(response.content)
        for icon in data["icons"]:
            assert "src" in icon
            assert "sizes" in icon
            assert "type" in icon


class TestServiceWorkerEndpoint(TestCase):  # type: ignore[misc]  # untyped Django base
    """Validate the online-only service worker endpoint."""

    def test_service_worker_returns_200(self) -> None:
        """GET /service-worker.js must return HTTP 200."""
        response = self.client.get("/service-worker.js")
        assert response.status_code == 200

    def test_service_worker_content_type_is_javascript(self) -> None:
        """Service worker must be served with JavaScript content type."""
        response = self.client.get("/service-worker.js")
        assert "text/javascript" in response["Content-Type"]

    def test_service_worker_does_not_cache_clinical_content(self) -> None:
        """Service worker must NOT contain any offline caching logic.

        The service worker must use network-only fetch behavior, ensuring
        no clinical content is served from cache when offline.
        """
        response = self.client.get("/service-worker.js")
        content = response.content.decode()
        # Must not use Cache API for clinical content
        assert "caches.open" not in content
        assert "cache.addAll" not in content
        # Must pass-through to network
        assert "fetch(" in content

    def test_service_worker_has_install_handler(self) -> None:
        """Service worker must register an install event handler."""
        response = self.client.get("/service-worker.js")
        content = response.content.decode()
        assert "install" in content

    def test_service_worker_has_activate_handler(self) -> None:
        """Service worker must register an activate event handler."""
        response = self.client.get("/service-worker.js")
        content = response.content.decode()
        assert "activate" in content


class TestRemoteRolePagesIncludePWAMetadata(TestCase):  # type: ignore[misc]  # untyped Django base
    """Validate that remote-capable roles get PWA installability metadata."""

    def test_doctor_home_includes_manifest_link(self) -> None:
        """Doctor home page must include a manifest link in the HTML head."""
        User.objects.create_user(
            email="doctor@example.com", password="testpass123", role="doctor",
        )
        self.client.login(username="doctor@example.com", password="testpass123")
        response = self.client.get("/doctor/")
        content = response.content.decode()
        assert 'rel="manifest"' in content

    def test_manager_home_includes_manifest_link(self) -> None:
        """Manager home page must include a manifest link in the HTML head."""
        User.objects.create_user(
            email="manager@example.com", password="testpass123", role="manager",
        )
        self.client.login(username="manager@example.com", password="testpass123")
        response = self.client.get("/manager/")
        content = response.content.decode()
        assert 'rel="manifest"' in content

    def test_admin_home_includes_manifest_link(self) -> None:
        """Admin home page must include a manifest link in the HTML head."""
        User.objects.create_user(
            email="admin@example.com", password="testpass123", role="admin",
        )
        self.client.login(username="admin@example.com", password="testpass123")
        response = self.client.get("/admin/")
        content = response.content.decode()
        assert 'rel="manifest"' in content

    def test_doctor_home_includes_service_worker_registration(self) -> None:
        """Doctor home must register the service worker via JavaScript."""
        User.objects.create_user(
            email="doctor@example.com", password="testpass123", role="doctor",
        )
        self.client.login(username="doctor@example.com", password="testpass123")
        response = self.client.get("/doctor/")
        content = response.content.decode()
        assert "serviceWorker" in content

    def test_manager_home_includes_service_worker_registration(self) -> None:
        """Manager home must register the service worker via JavaScript."""
        User.objects.create_user(
            email="manager@example.com", password="testpass123", role="manager",
        )
        self.client.login(username="manager@example.com", password="testpass123")
        response = self.client.get("/manager/")
        content = response.content.decode()
        assert "serviceWorker" in content

    def test_admin_home_includes_service_worker_registration(self) -> None:
        """Admin home must register the service worker via JavaScript."""
        User.objects.create_user(
            email="admin@example.com", password="testpass123", role="admin",
        )
        self.client.login(username="admin@example.com", password="testpass123")
        response = self.client.get("/admin/")
        content = response.content.decode()
        assert "serviceWorker" in content

    def test_doctor_home_includes_mobile_meta_tags(self) -> None:
        """Doctor home must include mobile-capable PWA meta tags."""
        User.objects.create_user(
            email="doctor@example.com", password="testpass123", role="doctor",
        )
        self.client.login(username="doctor@example.com", password="testpass123")
        response = self.client.get("/doctor/")
        content = response.content.decode()
        assert 'apple-mobile-web-app-capable' in content
        assert 'theme-color' in content


class TestIntranetRolePagesExcludePWAMetadata(TestCase):  # type: ignore[misc]  # untyped Django base
    """Validate that intranet-only roles do NOT get PWA metadata."""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up SQLAlchemy database with migrations for NIR view tests."""
        super().setUpClass()
        cls._tmp_dir = tempfile.mkdtemp()
        cls._db_path = Path(cls._tmp_dir) / "test_pwa_intranet.sqlite"
        cls._sync_url = f"sqlite+pysqlite:///{cls._db_path}"
        cls._async_url = f"sqlite+aiosqlite:///{cls._db_path}"

        alembic_config = Config()
        alembic_config.set_main_option("script_location", "alembic")
        alembic_config.set_main_option("sqlalchemy.url", cls._sync_url)
        command.upgrade(alembic_config, "head")

    @classmethod
    def tearDownClass(cls) -> None:
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(cls._tmp_dir, ignore_errors=True)
        super().tearDownClass()

    def test_nir_home_excludes_manifest_link(self) -> None:
        """NIR home page must NOT include PWA manifest link."""
        os.environ["DATABASE_URL"] = self._async_url
        User.objects.create_user(
            email="nir@example.com", password="testpass123", role="nir",
        )
        self.client.login(username="nir@example.com", password="testpass123")
        response = self.client.get("/nir/")
        content = response.content.decode()
        assert 'rel="manifest"' not in content

    def test_scheduler_home_excludes_manifest_link(self) -> None:
        """Scheduler home page must NOT include PWA manifest link."""
        User.objects.create_user(
            email="scheduler@example.com", password="testpass123", role="scheduler",
        )
        self.client.login(username="scheduler@example.com", password="testpass123")
        response = self.client.get("/scheduler/")
        content = response.content.decode()
        assert 'rel="manifest"' not in content

    def test_nir_home_excludes_service_worker(self) -> None:
        """NIR home page must NOT register a service worker."""
        os.environ["DATABASE_URL"] = self._async_url
        User.objects.create_user(
            email="nir@example.com", password="testpass123", role="nir",
        )
        self.client.login(username="nir@example.com", password="testpass123")
        response = self.client.get("/nir/")
        content = response.content.decode()
        assert "serviceWorker" not in content

    def test_scheduler_home_excludes_service_worker(self) -> None:
        """Scheduler home page must NOT register a service worker."""
        User.objects.create_user(
            email="scheduler@example.com", password="testpass123", role="scheduler",
        )
        self.client.login(username="scheduler@example.com", password="testpass123")
        response = self.client.get("/scheduler/")
        content = response.content.decode()
        assert "serviceWorker" not in content


class TestRoleAwareInstalledEntryBehavior(TestCase):  # type: ignore[misc]  # untyped Django base
    """Validate that the installed PWA preserves role-aware entry with session."""

    def test_authenticated_doctor_root_resumes_role_surface(self) -> None:
        """Authenticated doctor opening the app root lands on /doctor/."""
        User.objects.create_user(
            email="doctor@example.com", password="testpass123", role="doctor",
        )
        self.client.login(username="doctor@example.com", password="testpass123")
        response = self.client.get("/")
        assert response.status_code == 302
        assert response.url == "/doctor/"

    def test_authenticated_manager_root_resumes_role_surface(self) -> None:
        """Authenticated manager opening the app root lands on /manager/."""
        User.objects.create_user(
            email="manager@example.com", password="testpass123", role="manager",
        )
        self.client.login(username="manager@example.com", password="testpass123")
        response = self.client.get("/")
        assert response.status_code == 302
        assert response.url == "/manager/"

    def test_authenticated_admin_root_resumes_role_surface(self) -> None:
        """Authenticated admin opening the app root lands on /admin/."""
        User.objects.create_user(
            email="admin@example.com", password="testpass123", role="admin",
        )
        self.client.login(username="admin@example.com", password="testpass123")
        response = self.client.get("/")
        assert response.status_code == 302
        assert response.url == "/admin/"

    def test_unauthenticated_root_redirects_to_login(self) -> None:
        """Unauthenticated user opening the PWA must be redirected to login."""
        response = self.client.get("/")
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_session_persists_across_page_navigation(self) -> None:
        """Doctor session must persist when navigating between pages."""
        User.objects.create_user(
            email="doctor@example.com", password="testpass123", role="doctor",
        )
        self.client.login(username="doctor@example.com", password="testpass123")

        # Navigate to doctor home
        response = self.client.get("/doctor/")
        assert response.status_code == 200

        # Session still valid for root redirect
        response = self.client.get("/")
        assert response.status_code == 302
        assert response.url == "/doctor/"
        assert "_auth_user_id" in self.client.session


class TestLoginAndSmokePagesExcludePWAMetadata(TestCase):  # type: ignore[misc]  # untyped Django base
    """Login and smoke pages must not include PWA metadata."""

    def test_login_page_excludes_manifest_link(self) -> None:
        """Login page must not include manifest link (not an app surface)."""
        response = self.client.get("/login/")
        content = response.content.decode()
        assert 'rel="manifest"' not in content

    def test_smoke_page_excludes_manifest_link(self) -> None:
        """Smoke/health endpoint must not include manifest link."""
        response = self.client.get("/smoke/")
        content = response.content.decode()
        assert "manifest" not in content
