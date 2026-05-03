"""Integration tests for manager/admin role-aware shell navigation.

TDD tests for slice 2.1 — validates that:
- Manager sees only dashboard/reporting links in the shell navigation;
- Admin sees dashboard + administrative areas (users, prompts) in the shell;
- Manager receives 403 on /admin/, /admin/users/, and /admin/prompts/;
- Admin receives 200 on /admin/, /admin/users/, and /admin/prompts/;
- Anonymous users are redirected to login for admin routes.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from alembic.config import Config
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from alembic import command

User = get_user_model()


class _ShellNavigationTestBase(TestCase):  # type: ignore[misc]
    """Base class with shared setup for shell navigation integration tests."""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up SQLAlchemy database with migrations for integration testing."""
        super().setUpClass()
        cls._tmp_dir = tempfile.mkdtemp()
        cls._db_path = Path(cls._tmp_dir) / "test_shell_navigation.sqlite"
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
        """Create test users for both roles."""
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

    def _get_sync_connection(self) -> sa.Connection:
        """Create a synchronous SQLAlchemy connection to the test database."""
        engine = sa.create_engine(self._sync_url)
        conn = engine.connect()
        return conn

    def _insert_case(
        self,
        connection: sa.Connection,
        *,
        case_id: str,
        status: str,
        updated_at: datetime,
        origin_source: str = "matrix",
        agency_record_number: str | None = None,
        structured_data_json: dict[str, object] | None = None,
        doctor_decision: str | None = None,
        doctor_admission_flow: str | None = None,
        appointment_status: str | None = None,
        room1_final_reply_event_id: str | None = None,
    ) -> None:
        """Insert a case row for testing."""
        connection.execute(
            sa.text(
                "INSERT INTO cases ("
                "case_id, status, origin_source, room1_origin_room_id, "
                "room1_origin_event_id, room1_sender_user_id, "
                "agency_record_number, structured_data_json, doctor_decision, "
                "doctor_admission_flow, appointment_status, "
                "room1_final_reply_event_id, "
                "created_at, updated_at"
                ") VALUES ("
                ":case_id, :status, :origin_source, '!room1:example.org', "
                ":origin_event_id, '@nir:example.org', "
                ":agency_record_number, :structured_data_json, :doctor_decision, "
                ":doctor_admission_flow, :appointment_status, "
                ":room1_final_reply_event_id, "
                ":created_at, :updated_at"
                ")"
            ),
            {
                "case_id": case_id,
                "status": status,
                "origin_source": origin_source,
                "origin_event_id": f"$origin-{case_id}",
                "agency_record_number": agency_record_number,
                "structured_data_json": (
                    json.dumps(structured_data_json, ensure_ascii=False)
                    if structured_data_json is not None
                    else None
                ),
                "doctor_decision": doctor_decision,
                "doctor_admission_flow": doctor_admission_flow,
                "appointment_status": appointment_status,
                "room1_final_reply_event_id": room1_final_reply_event_id,
                "created_at": updated_at,
                "updated_at": updated_at,
            },
        )


# ── Navigation visibility tests ───────────────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestManagerShellNavigation(_ShellNavigationTestBase):
    """Manager-only shell navigation visibility."""

    def test_manager_dashboard_page_shows_only_dashboard_navigation(self) -> None:
        """Manager dashboard page MUST include dashboard link and MUST NOT include admin links."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

        response = self.client.get("/manager/")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        # Manager sees dashboard link
        self.assertIn("Dashboard", content)
        # Manager does NOT see admin user/prompt links
        self.assertNotIn("/admin/users/", content)
        self.assertNotIn("/admin/prompts/", content)
        self.assertNotIn("Usuários", content)
        self.assertNotIn("Prompts", content)

    def test_manager_case_detail_page_shows_only_dashboard_navigation(self) -> None:
        """Manager case detail page MUST not expose admin navigation links."""
        self._set_env_database_url()
        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_DOCTOR",
                updated_at=now,
            )
            conn.commit()
        finally:
            conn.close()

        self.client.login(username="manager@example.com", password="testpass123")

        response = self.client.get(f"/manager/cases/{case_id}/")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        # Manager sees dashboard link in nav
        self.assertIn("Dashboard", content)
        # Manager does NOT see admin user/prompt links
        self.assertNotIn("/admin/users/", content)
        self.assertNotIn("/admin/prompts/", content)


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestAdminShellNavigation(_ShellNavigationTestBase):
    """Admin-specific shell navigation visibility."""

    def test_admin_dashboard_page_shows_admin_navigation(self) -> None:
        """Admin dashboard page MUST include both dashboard and admin links."""
        self._set_env_database_url()
        self.client.login(username="admin@example.com", password="testpass123")

        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        # Admin sees dashboard link
        self.assertIn("Dashboard", content)
        # Admin sees admin area links
        self.assertIn("/admin/users/", content)
        self.assertIn("/admin/prompts/", content)

    def test_admin_case_detail_page_shows_admin_navigation(self) -> None:
        """Admin case detail page MUST also include admin navigation links."""
        self._set_env_database_url()
        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_DOCTOR",
                updated_at=now,
            )
            conn.commit()
        finally:
            conn.close()

        self.client.login(username="admin@example.com", password="testpass123")

        response = self.client.get(f"/manager/cases/{case_id}/")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        # Admin sees dashboard link in nav
        self.assertIn("Dashboard", content)
        # Admin sees admin area links in nav
        self.assertIn("/admin/users/", content)
        self.assertIn("/admin/prompts/", content)


# ── Authorization enforcement tests ────────────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestAdminRoutesAuthorization(_ShellNavigationTestBase):
    """Authorization checks for admin-only routes."""

    def test_manager_receives_403_on_admin_users_page(self) -> None:
        """Manager requesting /admin/users/ MUST receive 403 Forbidden."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

        response = self.client.get("/admin/users/")

        self.assertEqual(response.status_code, 403)

    def test_manager_receives_403_on_admin_prompts_page(self) -> None:
        """Manager requesting /admin/prompts/ MUST receive 403 Forbidden."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

        response = self.client.get("/admin/prompts/")

        self.assertEqual(response.status_code, 403)

    def test_admin_receives_200_on_admin_users_placeholder(self) -> None:
        """Admin requesting /admin/users/ MUST receive 200 (placeholder page)."""
        self._set_env_database_url()
        self.client.login(username="admin@example.com", password="testpass123")

        response = self.client.get("/admin/users/")

        self.assertEqual(response.status_code, 200)

    def test_admin_receives_200_on_admin_prompts_placeholder(self) -> None:
        """Admin requesting /admin/prompts/ MUST receive 200 (placeholder page)."""
        self._set_env_database_url()
        self.client.login(username="admin@example.com", password="testpass123")

        response = self.client.get("/admin/prompts/")

        self.assertEqual(response.status_code, 200)

    def test_anonymous_redirected_to_login_for_admin_users(self) -> None:
        """Anonymous user requesting /admin/users/ MUST be redirected to login."""
        self._set_env_database_url()

        response = self.client.get("/admin/users/", follow=False)

        self.assertIn(response.status_code, (302, 303))

    def test_anonymous_redirected_to_login_for_admin_prompts(self) -> None:
        """Anonymous user requesting /admin/prompts/ MUST be redirected to login."""
        self._set_env_database_url()

        response = self.client.get("/admin/prompts/", follow=False)

        self.assertIn(response.status_code, (302, 303))

    def test_manager_receives_403_on_admin_landing(self) -> None:
        """Manager requesting /admin/ MUST receive 403 Forbidden."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 403)

    def test_admin_receives_200_on_admin_landing(self) -> None:
        """Admin requesting /admin/ MUST receive 200 (dashboard with admin nav)."""
        self._set_env_database_url()
        self.client.login(username="admin@example.com", password="testpass123")

        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 200)
