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
from collections.abc import Iterator
from contextlib import contextmanager
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

    @contextmanager
    def _sync_connection(self) -> Iterator[sa.Connection]:
        """Context manager for a synchronous SQLAlchemy connection to the test database.

        Yields a connection and guarantees the engine is disposed after use.
        """
        engine = sa.create_engine(self._sync_url)
        conn = engine.connect()
        try:
            yield conn
        finally:
            conn.close()
            engine.dispose()

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
        with self._sync_connection() as conn:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_DOCTOR",
                updated_at=now,
            )
            conn.commit()

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
        with self._sync_connection() as conn:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_DOCTOR",
                updated_at=now,
            )
            conn.commit()

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


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestAdminUserManagementConsolidation(_ShellNavigationTestBase):
    """Admin user-management consolidation tests for slice 3.1."""

    def test_admin_can_access_consolidated_user_management_surface(self) -> None:
        """Admin gets consolidated user-management HTML page."""
        self._set_env_database_url()
        self.client.login(username="admin@example.com", password="testpass123")

        response = self.client.get("/admin/users/")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("Gestão de Usuários", content)
        self.assertIn("Criar usuário", content)

    def test_manager_gets_403_on_consolidated_user_management_surface(self) -> None:
        """Manager is forbidden from admin user management."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

        response = self.client.get("/admin/users/")

        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_all_supported_roles(self) -> None:
        """Admin can create users for all supported roles."""
        self._set_env_database_url()
        self.client.login(username="admin@example.com", password="testpass123")

        for role in ("nir", "doctor", "scheduler", "manager", "admin"):
            response = self.client.post(
                "/admin/users/",
                {
                    "email": f"{role}.new@example.com",
                    "password": "testpass123",
                    "role": role,
                },
            )
            self.assertEqual(response.status_code, 302)

        created_roles = {
            user.email: user.role
            for user in User.objects.filter(
                email__in=[
                    "nir.new@example.com",
                    "doctor.new@example.com",
                    "scheduler.new@example.com",
                    "manager.new@example.com",
                    "admin.new@example.com",
                ]
            )
        }

        self.assertEqual(created_roles["nir.new@example.com"], "nir")
        self.assertEqual(created_roles["doctor.new@example.com"], "doctor")
        self.assertEqual(created_roles["scheduler.new@example.com"], "scheduler")
        self.assertEqual(created_roles["manager.new@example.com"], "manager")
        self.assertEqual(created_roles["admin.new@example.com"], "admin")

    def test_admin_can_change_user_role_to_supported_role(self) -> None:
        """Admin can update an existing user's role to another supported role."""
        self._set_env_database_url()
        target = User.objects.create_user(
            email="rolechange@example.com",
            password="testpass123",
            role="nir",
        )
        self.client.login(username="admin@example.com", password="testpass123")

        response = self.client.post(
            f"/admin/users/{target.pk}/role/",
            {"role": "doctor"},
        )

        self.assertEqual(response.status_code, 302)
        target.refresh_from_db()
        self.assertEqual(target.role, "doctor")

    def test_role_change_preserves_last_active_admin_invariant(self) -> None:
        """Changing the last active admin to non-admin is rejected."""
        self._set_env_database_url()
        self.client.login(username="admin@example.com", password="testpass123")

        response = self.client.post(
            f"/admin/users/{self.admin_user.pk}/role/",
            {"role": "manager"},
        )

        self.assertEqual(response.status_code, 302)
        self.admin_user.refresh_from_db()
        self.assertEqual(self.admin_user.role, "admin")

    def test_create_user_audit_contract_matches_user_management_pattern(self) -> None:
        """Create-user audit payload includes actor attribution and target metadata
        matching the UserManagementService audit contract."""
        self._set_env_database_url()
        self.client.login(username="admin@example.com", password="testpass123")

        self.client.post(
            "/admin/users/",
            {"email": "audit.test@example.com", "password": "testpass123", "role": "doctor"},
        )

        with self._sync_connection() as conn:
            row = conn.execute(
                sa.text(
                    "SELECT event_type, payload FROM auth_events "
                    "WHERE event_type = 'user_created' ORDER BY id DESC LIMIT 1"
                )
            ).mappings().first()

        self.assertIsNotNone(row)
        self.assertEqual(row["event_type"], "user_created")
        payload = json.loads(row["payload"]) if isinstance(row["payload"], str) else row["payload"]
        # Contract: target metadata
        self.assertIn("target_user_id", payload)
        self.assertIn("target_email", payload)
        self.assertIn("target_role", payload)
        self.assertEqual(payload["target_email"], "audit.test@example.com")
        self.assertEqual(payload["target_role"], "doctor")
        # Contract: actor attribution
        self.assertIn("actor_email", payload)
        self.assertEqual(payload["actor_email"], "admin@example.com")
        self.assertIn("actor_user_id", payload)
        self.assertIsNotNone(payload["actor_user_id"])
        # Contract: status fields (user_created starts active)
        self.assertIsNone(payload.get("previous_status"))
        self.assertEqual(payload.get("new_status"), "active")

    def test_block_user_audit_records_status_transition(self) -> None:
        """Block audit event records active→blocked transition with proper contract."""
        self._set_env_database_url()
        target = User.objects.create_user(
            email="block-audit@example.com",
            password="testpass123",
            role="scheduler",
        )
        self.client.login(username="admin@example.com", password="testpass123")

        self.client.post(f"/admin/users/{target.pk}/block/")

        with self._sync_connection() as conn:
            row = conn.execute(
                sa.text(
                    "SELECT event_type, payload FROM auth_events "
                    "WHERE event_type = 'user_blocked' ORDER BY id DESC LIMIT 1"
                )
            ).mappings().first()

        self.assertIsNotNone(row)
        payload = json.loads(row["payload"]) if isinstance(row["payload"], str) else row["payload"]
        self.assertEqual(payload["target_email"], "block-audit@example.com")
        self.assertEqual(payload["previous_status"], "active")
        self.assertEqual(payload["new_status"], "blocked")
        self.assertEqual(payload["actor_email"], "admin@example.com")
        self.assertIn("target_user_id", payload)
        self.assertIsNotNone(payload["target_user_id"])

    def test_activate_user_audit_records_status_transition(self) -> None:
        """Activate audit event records blocked→active transition."""
        self._set_env_database_url()
        target = User.objects.create_user(
            email="activate-audit@example.com",
            password="testpass123",
            role="doctor",
        )
        target.is_active = False
        target.save()
        self.client.login(username="admin@example.com", password="testpass123")

        self.client.post(f"/admin/users/{target.pk}/activate/")

        with self._sync_connection() as conn:
            row = conn.execute(
                sa.text(
                    "SELECT event_type, payload FROM auth_events "
                    "WHERE event_type = 'user_reactivated' ORDER BY id DESC LIMIT 1"
                )
            ).mappings().first()

        self.assertIsNotNone(row)
        payload = json.loads(row["payload"]) if isinstance(row["payload"], str) else row["payload"]
        self.assertEqual(payload["target_email"], "activate-audit@example.com")
        self.assertEqual(payload["previous_status"], "blocked")
        self.assertEqual(payload["new_status"], "active")
        self.assertEqual(payload["actor_email"], "admin@example.com")

    def test_role_change_audit_records_old_and_new_role(self) -> None:
        """Role change audit event records old_role→new_role transition."""
        self._set_env_database_url()
        target = User.objects.create_user(
            email="role-audit@example.com",
            password="testpass123",
            role="nir",
        )
        self.client.login(username="admin@example.com", password="testpass123")

        self.client.post(f"/admin/users/{target.pk}/role/", {"role": "doctor"})

        with self._sync_connection() as conn:
            row = conn.execute(
                sa.text(
                    "SELECT event_type, payload FROM auth_events "
                    "WHERE event_type = 'user_role_changed' ORDER BY id DESC LIMIT 1"
                )
            ).mappings().first()

        self.assertIsNotNone(row)
        payload = json.loads(row["payload"]) if isinstance(row["payload"], str) else row["payload"]
        self.assertEqual(payload["target_email"], "role-audit@example.com")
        self.assertEqual(payload["actor_email"], "admin@example.com")
        self.assertEqual(payload["old_role"], "nir")
        self.assertEqual(payload["new_role"], "doctor")
        self.assertIn("target_user_id", payload)
        self.assertIsNotNone(payload["target_user_id"])

    def test_admin_can_block_user(self) -> None:
        """Admin can block an existing user."""
        self._set_env_database_url()
        target = User.objects.create_user(
            email="blockable@example.com",
            password="testpass123",
            role="doctor",
        )
        self.client.login(username="admin@example.com", password="testpass123")

        response = self.client.post(f"/admin/users/{target.pk}/block/")

        self.assertEqual(response.status_code, 302)
        target.refresh_from_db()
        self.assertFalse(target.is_active)

    def test_admin_can_reactivate_user(self) -> None:
        """Admin can reactivate a blocked user."""
        self._set_env_database_url()
        target = User.objects.create_user(
            email="reactivatable@example.com",
            password="testpass123",
            role="scheduler",
        )
        target.is_active = False
        target.save()
        self.client.login(username="admin@example.com", password="testpass123")

        response = self.client.post(f"/admin/users/{target.pk}/activate/")

        self.assertEqual(response.status_code, 302)
        target.refresh_from_db()
        self.assertTrue(target.is_active)

    def test_admin_block_preserves_last_admin_invariant(self) -> None:
        """Blocking the last active admin is rejected."""
        self._set_env_database_url()
        self.client.login(username="admin@example.com", password="testpass123")

        response = self.client.post(f"/admin/users/{self.admin_user.pk}/block/")

        self.assertEqual(response.status_code, 302)
        self.admin_user.refresh_from_db()
        self.assertTrue(self.admin_user.is_active)

    def test_manager_cannot_block_user(self) -> None:
        """Manager receives 403 when attempting to block a user."""
        self._set_env_database_url()
        target = User.objects.create_user(
            email="manager-target@example.com",
            password="testpass123",
            role="doctor",
        )
        self.client.login(username="manager@example.com", password="testpass123")

        response = self.client.post(f"/admin/users/{target.pk}/block/")

        self.assertEqual(response.status_code, 403)

    def test_legacy_reader_role_is_supported_for_create(self) -> None:
        """The domain Role enum includes READER for legacy mapping support."""
        self._set_env_database_url()
        self.client.login(username="admin@example.com", password="testpass123")

        # The "reader" role should be accepted and mapped to "manager"
        response = self.client.post(
            "/admin/users/",
            {"email": "legacy.reader@example.com", "password": "testpass123", "role": "reader"},
        )

        self.assertEqual(response.status_code, 302)
        created = User.objects.get(email="legacy.reader@example.com")
        # Legacy reader is mapped to manager
        self.assertEqual(created.role, "manager")
