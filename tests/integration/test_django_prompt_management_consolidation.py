"""Integration tests for Django consolidated prompt-management surface.

TDD tests for slice 3.2 — validates that:
- Admin can access the prompt-management HTML page and see prompt versions.
- Admin can activate a prompt version from the HTML form.
- Admin can create a new prompt version from the HTML form.
- Manager receives 403 on prompt-management page and cannot mutate state.
- Prompt audit events are preserved for admin mutations.
- The implementation does not depend on legacy FastAPI surface.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from alembic.config import Config
from django.contrib.auth import get_user_model
from django.test import TestCase

from alembic import command

User = get_user_model()


class _PromptManagementTestBase(TestCase):  # type: ignore[misc]
    """Base class with shared setup for Django prompt-management integration tests."""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up SQLAlchemy database with migrations for integration testing."""
        super().setUpClass()
        cls._tmp_dir = tempfile.mkdtemp()
        cls._db_path = Path(cls._tmp_dir) / "test_prompt_management.sqlite"
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

    def setUp(self) -> None:
        """Create test users for manager and admin roles."""
        super().setUp()
        self.manager_user = User.objects.create_user(
            email="manager@example.com",
            password="testpass123",
            role="manager",
        )
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="testpass123",
            role="admin",
        )

    def _set_env_database_url(self) -> None:
        """Set DATABASE_URL environment variable for service wiring."""
        os.environ["DATABASE_URL"] = self._async_url

    @contextmanager
    def _sync_connection(self) -> Iterator[sa.Connection]:
        """Context manager for a synchronous SQLAlchemy connection."""
        engine = sa.create_engine(self._sync_url)
        conn = engine.connect()
        try:
            yield conn
        finally:
            conn.close()
            engine.dispose()

    def _insert_prompt_template(
        self,
        connection: sa.Connection,
        *,
        prompt_name: str,
        version: int,
        content: str,
        is_active: bool,
    ) -> None:
        """Insert a prompt template version into the shared test database."""
        now = datetime.now(tz=UTC)
        connection.execute(
            sa.text(
                "INSERT INTO prompt_templates "
                "(id, name, version, content, is_active, created_at, updated_at) "
                "VALUES (:id, :name, :version, :content, :is_active, :created_at, :updated_at)"
            ),
            {
                "id": uuid4().hex,
                "name": prompt_name,
                "version": version,
                "content": content,
                "is_active": is_active,
                "created_at": now,
                "updated_at": now,
            },
        )
        connection.commit()

    def _get_prompt_versions(
        self, connection: sa.Connection, *, prompt_name: str
    ) -> dict[int, dict[str, object]]:
        """Return version → {is_active, content} mapping for a prompt name."""
        rows = connection.execute(
            sa.text(
                "SELECT version, is_active, content FROM prompt_templates "
                "WHERE name = :name ORDER BY version"
            ),
            {"name": prompt_name},
        ).mappings()
        return {
            int(row["version"]): {
                "is_active": bool(row["is_active"]),
                "content": str(row["content"]),
            }
            for row in rows
        }

    def _get_latest_auth_event(
        self, connection: sa.Connection
    ) -> dict[str, object]:
        """Return the latest auth_event row as a dict."""
        row = connection.execute(
            sa.text(
                "SELECT user_id, event_type, payload, occurred_at "
                "FROM auth_events ORDER BY id DESC LIMIT 1"
            )
        ).mappings().one()
        payload = (
            row["payload"]
            if isinstance(row["payload"], dict)
            else json.loads(str(row["payload"]))
        )
        return {
            "user_id": row["user_id"],
            "event_type": row["event_type"],
            "payload": payload,
            "occurred_at": row["occurred_at"],
        }


# ── Authorization tests ─────────────────────────────────────────────


class TestAdminCanAccessPromptManagementPage(_PromptManagementTestBase):
    """Admin must be able to access the prompt-management HTML surface."""

    def test_admin_renders_prompt_management_page(self) -> None:
        """Admin GET /admin/prompts/ returns 200 with prompt list."""
        self._set_env_database_url()
        self.client.login(username="admin@example.com", password="testpass123")

        # llm1_system v1-v6 already seeded by Alembic migrations.
        # Insert an additional inactive version.
        with self._sync_connection() as conn:
            self._insert_prompt_template(
                conn,
                prompt_name="llm1_system",
                version=7,
                content="test llm1_system v7",
                is_active=False,
            )

        response = self.client.get("/admin/prompts/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response["Content-Type"])
        content = response.content.decode()
        self.assertIn("Gestão de Prompts", content)
        self.assertIn("llm1_system", content)


class TestManagerCannotAccessPromptManagement(_PromptManagementTestBase):
    """Manager must receive 403 on prompt-management surface."""

    def test_manager_receives_403_on_prompt_management_page(self) -> None:
        """Manager GET /admin/prompts/ returns 403."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

        response = self.client.get("/admin/prompts/")

        self.assertEqual(response.status_code, 403)

    def test_manager_cannot_activate_prompt_and_state_unchanged(self) -> None:
        """Manager POST to activate-form is rejected and DB state unchanged."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

        # llm2_user v1-v3 seeded. Insert v4 as inactive.
        with self._sync_connection() as conn:
            self._insert_prompt_template(
                conn,
                prompt_name="llm2_user",
                version=4,
                content="inactive llm2_user v4",
                is_active=False,
            )

        response = self.client.post(
            "/admin/prompts/llm2_user/activate/",
            {"version": "4"},
        )

        self.assertEqual(response.status_code, 403)

        with self._sync_connection() as conn:
            versions = self._get_prompt_versions(conn, prompt_name="llm2_user")

        self.assertTrue(versions[3]["is_active"])
        self.assertFalse(versions[4]["is_active"])
        active_count = sum(1 for v in versions.values() if v["is_active"])
        self.assertEqual(active_count, 1)


class TestAnonymousRedirectedToLoginForPrompts(_PromptManagementTestBase):
    """Anonymous users must be redirected to login for admin prompts route."""

    def test_anonymous_redirected_to_login(self) -> None:
        """Unauthenticated GET /admin/prompts/ redirects to login."""
        self._set_env_database_url()

        response = self.client.get("/admin/prompts/", follow=False)

        self.assertIn(response.status_code, (302, 303))


# ── Prompt activation tests ─────────────────────────────────────────


class TestAdminActivatesPromptVersion(_PromptManagementTestBase):
    """Admin must be able to activate a prompt version via HTML form."""

    def test_admin_activation_form_activates_version_and_redirects(self) -> None:
        """POST to activate-form changes active version and redirects."""
        self._set_env_database_url()
        self.client.login(username="admin@example.com", password="testpass123")

        # llm2_system v1-v3 seeded. Insert v4 as inactive.
        with self._sync_connection() as conn:
            self._insert_prompt_template(
                conn,
                prompt_name="llm2_system",
                version=4,
                content="inactive llm2_system v4",
                is_active=False,
            )

        response = self.client.post(
            "/admin/prompts/llm2_system/activate/",
            {"version": "4"},
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/prompts/", response.url or "")

        with self._sync_connection() as conn:
            versions = self._get_prompt_versions(conn, prompt_name="llm2_system")

        self.assertFalse(versions[3]["is_active"])
        self.assertTrue(versions[4]["is_active"])
        active_count = sum(1 for v in versions.values() if v["is_active"])
        self.assertEqual(active_count, 1)

    def test_admin_activates_version_with_invalid_version_key(self) -> None:
        """POST with missing version field redirects with error."""
        self._set_env_database_url()
        self.client.login(username="admin@example.com", password="testpass123")

        response = self.client.post(
            "/admin/prompts/llm2_system/activate/",
            {},
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("error", (response.url or "").lower())

    def test_admin_activates_nonexistent_version_redirects_with_error(self) -> None:
        """POST with version that does not exist redirects with error."""
        self._set_env_database_url()
        self.client.login(username="admin@example.com", password="testpass123")

        response = self.client.post(
            "/admin/prompts/llm2_system/activate/",
            {"version": "99"},
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("error", (response.url or "").lower())


# ── Prompt version detail tests ─────────────────────────────────────


class TestAdminViewsPromptVersionDetail(_PromptManagementTestBase):
    """Admin must be able to view prompt version content and create form."""

    def test_admin_renders_prompt_version_detail_page(self) -> None:
        """GET /admin/prompts/{name}/versions/{v} renders content and create form."""
        self._set_env_database_url()
        self.client.login(username="admin@example.com", password="testpass123")

        # llm1_user v1-v6 seeded. Insert v7 as inactive with custom content.
        with self._sync_connection() as conn:
            self._insert_prompt_template(
                conn,
                prompt_name="llm1_user",
                version=7,
                content="PROMPT V7 CUSTOM CONTENT",
                is_active=False,
            )

        response = self.client.get("/admin/prompts/llm1_user/versions/7/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response["Content-Type"])
        content = response.content.decode()
        self.assertIn("Conteúdo do Prompt", content)
        self.assertIn("llm1_user", content)
        self.assertIn("PROMPT V7 CUSTOM CONTENT", content)
        self.assertIn("Criar nova versão", content)

    def test_admin_views_nonexistent_version_redirects_to_list(self) -> None:
        """GET nonexistent version redirects to prompt list with error."""
        self._set_env_database_url()
        self.client.login(username="admin@example.com", password="testpass123")

        response = self.client.get(
            "/admin/prompts/llm1_user/versions/99/",
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/prompts/", response.url or "")

    def test_manager_blocked_from_version_detail(self) -> None:
        """Manager GET version detail receives 403."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

        # llm1_user v6 is already seeded and active.
        response = self.client.get("/admin/prompts/llm1_user/versions/6/")

        self.assertEqual(response.status_code, 403)


# ── Prompt creation tests ───────────────────────────────────────────


class TestAdminCreatesPromptVersion(_PromptManagementTestBase):
    """Admin must be able to create a new prompt version from HTML form."""

    def test_admin_create_form_inserts_new_version_and_redirects(self) -> None:
        """POST to create-form inserts new inactive version and redirects."""
        self._set_env_database_url()
        self.client.login(username="admin@example.com", password="testpass123")

        # llm2_user v3 already seeded by Alembic as active.
        response = self.client.post(
            "/admin/prompts/llm2_user/create/",
            {
                "source_version": "3",
                "content": "NOVA VERSAO DERIVADA DA V3",
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/prompts/", response.url or "")

        with self._sync_connection() as conn:
            versions = self._get_prompt_versions(conn, prompt_name="llm2_user")

        self.assertIn(4, versions)
        self.assertEqual(versions[4]["content"], "NOVA VERSAO DERIVADA DA V3")
        self.assertFalse(versions[4]["is_active"])
        active_count = sum(1 for v in versions.values() if v["is_active"])
        self.assertEqual(active_count, 1)

    def test_admin_create_form_with_empty_content_redirects_with_error(self) -> None:
        """POST with empty content redirects to version detail with error."""
        self._set_env_database_url()
        self.client.login(username="admin@example.com", password="testpass123")

        # llm2_user v3 already seeded by Alembic.
        response = self.client.post(
            "/admin/prompts/llm2_user/create/",
            {"source_version": "3", "content": "   "},
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        # Should redirect back to version detail with error
        self.assertIn("versions/3", response.url or "")
        self.assertIn("error", (response.url or "").lower())

    def test_manager_blocked_from_creating_prompt(self) -> None:
        """Manager POST to create-form receives 403."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

        # llm2_user v3 already seeded.
        # Capture existing versions count before attempted mutation.
        with self._sync_connection() as conn:
            pre_versions = self._get_prompt_versions(conn, prompt_name="llm2_user")
        pre_count = len(pre_versions)

        response = self.client.post(
            "/admin/prompts/llm2_user/create/",
            {"source_version": "3", "content": "SHOULD NOT PERSIST"},
        )

        self.assertEqual(response.status_code, 403)

        with self._sync_connection() as conn:
            post_versions = self._get_prompt_versions(conn, prompt_name="llm2_user")

        self.assertEqual(len(post_versions), pre_count)


# ── Audit preservation tests ────────────────────────────────────────


class TestPromptActivationAuditPreserved(_PromptManagementTestBase):
    """Prompt activation must produce an audit event."""

    def test_admin_activation_appends_prompt_audit_event(self) -> None:
        """Activation via form writes auth_events with prompt_version_activated."""
        self._set_env_database_url()
        self.client.login(username="admin@example.com", password="testpass123")

        # llm1_user v1-v6 seeded (v6 active). Insert v7 as inactive.
        with self._sync_connection() as conn:
            self._insert_prompt_template(
                conn,
                prompt_name="llm1_user",
                version=7,
                content="inactive llm1_user v7 for audit test",
                is_active=False,
            )

        response = self.client.post(
            "/admin/prompts/llm1_user/activate/",
            {"version": "7"},
            follow=False,
        )

        self.assertEqual(response.status_code, 302)

        with self._sync_connection() as conn:
            event = self._get_latest_auth_event(conn)

        self.assertIsNone(event["user_id"])
        self.assertEqual(event["event_type"], "prompt_version_activated")
        payload = event["payload"]
        assert isinstance(payload, dict)
        self.assertIn("action", payload)
        self.assertIn("prompt_name", payload)
        self.assertIn("version", payload)
        self.assertIn("actor_user_id", payload)
        self.assertIn("actor_email", payload)
        self.assertIsNotNone(event["occurred_at"])


class TestPromptCreationAuditPreserved(_PromptManagementTestBase):
    """Prompt creation must produce an audit event."""

    def test_admin_creation_appends_prompt_audit_event(self) -> None:
        """Creation via form writes auth_events with prompt_version_created."""
        self._set_env_database_url()
        self.client.login(username="admin@example.com", password="testpass123")

        with self._sync_connection() as conn:
            self._insert_prompt_template(
                conn,
                prompt_name="custom_audit_prompt",
                version=1,
                content="BASE V1",
                is_active=True,
            )

        response = self.client.post(
            "/admin/prompts/custom_audit_prompt/create/",
            {
                "source_version": "1",
                "content": "AUDITABLE NEW VERSION",
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)

        with self._sync_connection() as conn:
            event = self._get_latest_auth_event(conn)

        self.assertIsNone(event["user_id"])
        self.assertEqual(event["event_type"], "prompt_version_created")
        payload = event["payload"]
        assert isinstance(payload, dict)
        self.assertIn("action", payload)
        self.assertIn("prompt_name", payload)
        self.assertIn("source_version", payload)
        self.assertIn("version", payload)
        self.assertIn("actor_user_id", payload)
        self.assertIn("actor_email", payload)
        self.assertIsNotNone(event["occurred_at"])


# ── Navigation/shell coherency tests ────────────────────────────────


class TestPromptPageShellNavigationCoherent(_PromptManagementTestBase):
    """Navigation must be coherent for the consolidated Django surface."""

    def test_admin_prompt_page_includes_dashboard_nav(self) -> None:
        """Admin prompt page must include dashboard navigation link."""
        self._set_env_database_url()
        self.client.login(username="admin@example.com", password="testpass123")

        response = self.client.get("/admin/prompts/")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("/manager/", content)

    def test_admin_prompt_page_includes_user_and_prompt_nav(self) -> None:
        """Admin prompt page must include admin nav links."""
        self._set_env_database_url()
        self.client.login(username="admin@example.com", password="testpass123")

        response = self.client.get("/admin/prompts/")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("/admin/users/", content)
        self.assertIn("/admin/prompts/", content)

    def test_activation_page_shows_recent_versions_with_active_visible(self) -> None:
        """Prompt listing shows versions with active-version highlight and toggle."""
        self._set_env_database_url()
        self.client.login(username="admin@example.com", password="testpass123")

        with self._sync_connection() as conn:
            for version in range(1, 13):
                self._insert_prompt_template(
                    conn,
                    prompt_name="custom_prompt_long",
                    version=version,
                    content=f"custom prompt long v{version}",
                    is_active=(version == 2),
                )

        response = self.client.get("/admin/prompts/")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Active version row should be visible
        self.assertRegex(
            content,
            r'data-row-id="custom_prompt_long-2"[\s\S]*?data-initial-visibility="visible"',
        )
        # Older version beyond limit should be hidden
        self.assertRegex(
            content,
            r'data-row-id="custom_prompt_long-4"[\s\S]*?data-initial-visibility="hidden"',
        )
