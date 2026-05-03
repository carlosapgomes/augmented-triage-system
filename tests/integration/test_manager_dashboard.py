"""Integration tests for manager/admin consolidated dashboard listing.

TDD tests for slice 1.1 — validates that:
- Manager user can access the dashboard page;
- Admin user can access the dashboard page;
- Non-manager/admin roles (nir, doctor, scheduler) receive 403;
- Anonymous users are redirected to login;
- Dashboard lists cases ordered by latest activity descending;
- Dashboard includes operational totals;
- Manager access remains read-only (no mutation endpoints).
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from alembic.config import Config
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from alembic import command

User = get_user_model()


class _ManagerDashboardTestBase(TestCase):  # type: ignore[misc]
    """Base class with shared setup for manager dashboard integration tests."""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up SQLAlchemy database with migrations for integration testing."""
        super().setUpClass()
        cls._tmp_dir = tempfile.mkdtemp()
        cls._db_path = Path(cls._tmp_dir) / "test_manager_dashboard.sqlite"
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
        """Create test users."""
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
        self.nir_user = User.objects.create_user(
            email="nir@example.com",
            password="testpass123",
            role="nir",
        )
        self.doctor_user = User.objects.create_user(
            email="doctor@example.com",
            password="testpass123",
            role="doctor",
        )
        self.scheduler_user = User.objects.create_user(
            email="scheduler@example.com",
            password="testpass123",
            role="scheduler",
        )

    def _get_sync_connection(self) -> sa.Connection:
        """Create a synchronous SQLAlchemy connection to the test database."""
        engine = sa.create_engine(self._sync_url)
        conn = engine.connect()
        return conn

    def _set_env_database_url(self) -> None:
        """Set DATABASE_URL environment variable for service wiring."""
        os.environ["DATABASE_URL"] = self._async_url

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

    def _insert_matrix_transcript(
        self,
        connection: sa.Connection,
        *,
        case_id: str,
        event_id: str,
        message_type: str = "room2_doctor_reply",
        captured_at: datetime | None = None,
    ) -> None:
        """Insert a matrix message transcript for timeline testing."""
        if captured_at is None:
            captured_at = datetime.now(tz=UTC)
        connection.execute(
            sa.text(
                "INSERT INTO case_matrix_message_transcripts ("
                "case_id, room_id, event_id, sender, sender_display_name, "
                "message_type, message_text, captured_at"
                ") VALUES ("
                ":case_id, '!room2:example.org', :event_id, '@doctor:example.org', "
                "'Dr. Carlos', :message_type, 'ok', :captured_at"
                ")"
            ),
            {
                "case_id": case_id,
                "event_id": event_id,
                "message_type": message_type,
                "captured_at": captured_at,
            },
        )

    def _insert_case_event(
        self,
        connection: sa.Connection,
        *,
        case_id: str,
        event_type: str,
        actor_user_id: str,
        payload: str,
        ts: datetime,
        actor_type: str = "web_human",
    ) -> None:
        """Insert a case_events row for timeline testing."""
        connection.execute(
            sa.text(
                "INSERT INTO case_events ("
                "case_id, actor_type, event_type, actor_user_id, payload, ts"
                ") VALUES ("
                ":case_id, :actor_type, :event_type, :actor_user_id, "
                ":payload, :ts"
                ")"
            ),
            {
                "case_id": case_id,
                "actor_type": actor_type,
                "event_type": event_type,
                "actor_user_id": actor_user_id,
                "payload": payload,
                "ts": ts,
            },
        )


# ── Access Control ─────────────────────────────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestManagerDashboardAccessControl(_ManagerDashboardTestBase):
    """Access control for manager dashboard."""

    def test_manager_dashboard_returns_200_for_manager_user(self) -> None:
        """Manager user can access the dashboard page."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

        response = self.client.get("/manager/")

        self.assertEqual(response.status_code, 200)

    def test_manager_dashboard_returns_200_for_admin_user(self) -> None:
        """Admin user can also access the manager dashboard page."""
        self._set_env_database_url()
        self.client.login(username="admin@example.com", password="testpass123")

        response = self.client.get("/manager/")

        self.assertEqual(response.status_code, 200)

    def test_manager_dashboard_rejects_nir_role(self) -> None:
        """NIR role receives 403 Forbidden on manager dashboard."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        response = self.client.get("/manager/")

        self.assertEqual(response.status_code, 403)

    def test_manager_dashboard_rejects_doctor_role(self) -> None:
        """Doctor role receives 403 Forbidden on manager dashboard."""
        self._set_env_database_url()
        self.client.login(username="doctor@example.com", password="testpass123")

        response = self.client.get("/manager/")

        self.assertEqual(response.status_code, 403)

    def test_manager_dashboard_rejects_scheduler_role(self) -> None:
        """Scheduler role receives 403 Forbidden on manager dashboard."""
        self._set_env_database_url()
        self.client.login(username="scheduler@example.com", password="testpass123")

        response = self.client.get("/manager/")

        self.assertEqual(response.status_code, 403)

    def test_manager_dashboard_requires_authentication(self) -> None:
        """Anonymous users are redirected to login."""
        response = self.client.get("/manager/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)


# ── Case Listing ──────────────────────────────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestManagerDashboardCaseList(_ManagerDashboardTestBase):
    """Manager dashboard shows consolidated case listing."""

    def test_manager_dashboard_shows_cases(self) -> None:
        """Cases appear in the manager dashboard listing."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_DOCTOR",
                updated_at=now,
                agency_record_number="REG-001",
            )
            self._insert_matrix_transcript(
                conn,
                case_id=case_id.hex,
                event_id="$evt-wait-doctor",
                captured_at=now,
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get("/manager/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(case_id))

    def test_manager_dashboard_includes_cleaned_cases(self) -> None:
        """Manager can see CLEANED cases (unlike NIR which filters them out)."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="CLEANED",
                updated_at=now,
                agency_record_number="REG-002",
            )
            self._insert_matrix_transcript(
                conn,
                case_id=case_id.hex,
                event_id="$evt-cleaned",
                captured_at=now,
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get("/manager/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(case_id))

    def test_manager_dashboard_orders_by_latest_activity_desc(self) -> None:
        """Most recently active cases appear first."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

        older_id = uuid4()
        newer_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=older_id.hex,
                status="WAIT_DOCTOR",
                updated_at=now - timedelta(hours=2),
                agency_record_number="REG-OLDER",
            )
            self._insert_matrix_transcript(
                conn,
                case_id=older_id.hex,
                event_id="$evt-older",
                captured_at=now - timedelta(hours=2),
            )
            self._insert_case(
                conn,
                case_id=newer_id.hex,
                status="WAIT_APPT",
                updated_at=now - timedelta(hours=1),
                agency_record_number="REG-NEWER",
            )
            self._insert_matrix_transcript(
                conn,
                case_id=newer_id.hex,
                event_id="$evt-newer",
                captured_at=now - timedelta(hours=1),
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get("/manager/")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        pos_newer = content.find(str(newer_id))
        pos_older = content.find(str(older_id))
        self.assertGreater(pos_newer, -1, "Newer case should be in response")
        self.assertGreater(pos_older, -1, "Older case should be in response")
        self.assertLess(pos_newer, pos_older, "Newer case should appear first")

    def test_manager_dashboard_shows_patient_name(self) -> None:
        """Dashboard shows patient name from structured data."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_DOCTOR",
                updated_at=now,
                agency_record_number="REG-004",
                structured_data_json={
                    "patient": {"name": "Maria Souza", "age": 54},
                },
            )
            self._insert_matrix_transcript(
                conn,
                case_id=case_id.hex,
                event_id="$evt-patient",
                captured_at=now,
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get("/manager/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Maria Souza")

    def test_manager_dashboard_shows_record_number(self) -> None:
        """Dashboard shows agency record number."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_DOCTOR",
                updated_at=now,
                agency_record_number="2026-0503-001",
            )
            self._insert_matrix_transcript(
                conn,
                case_id=case_id.hex,
                event_id="$evt-record",
                captured_at=now,
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get("/manager/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2026-0503-001")


# ── Totals ─────────────────────────────────────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestManagerDashboardTotals(_ManagerDashboardTestBase):
    """Manager dashboard shows operational totals."""

    def test_manager_dashboard_shows_totals(self) -> None:
        """Dashboard includes operational totals section."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

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
            self._insert_matrix_transcript(
                conn,
                case_id=case_id.hex,
                event_id="$evt-totals",
                captured_at=now,
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get("/manager/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Total de casos")

    def test_manager_dashboard_shows_operational_status(self) -> None:
        """Dashboard shows operational status labels."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

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
            self._insert_matrix_transcript(
                conn,
                case_id=case_id.hex,
                event_id="$evt-status",
                captured_at=now,
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get("/manager/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WAIT_DOCTOR")


# ── Read-only enforcement ──────────────────────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestManagerDashboardReadOnly(_ManagerDashboardTestBase):
    """Manager dashboard is strictly read-only (no mutations)."""

    def test_manager_dashboard_no_mutation_forms(self) -> None:
        """Dashboard page contains no case-mutation forms (upload, decision, etc.)."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

        response = self.client.get("/manager/")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # No case upload or decision mutation forms
        self.assertNotIn("enviar", content.lower())
        self.assertNotIn('action="/nir/', content.lower())
        self.assertNotIn('action="/doctor/', content.lower())
        self.assertNotIn('action="/scheduler/', content.lower())
        # No PDF upload file inputs
        self.assertNotIn('type="file"', content.lower())


# ── Admin also accesses same dashboard ─────────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestAdminDashboardAccess(_ManagerDashboardTestBase):
    """Admin can also access the consolidated dashboard."""

    def test_admin_dashboard_shows_cases(self) -> None:
        """Admin sees the same dashboard listing as manager."""
        self._set_env_database_url()
        self.client.login(username="admin@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_DOCTOR",
                updated_at=now,
                agency_record_number="REG-ADMIN-001",
            )
            self._insert_matrix_transcript(
                conn,
                case_id=case_id.hex,
                event_id="$evt-admin",
                captured_at=now,
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(case_id))
        self.assertContains(response, "REG-ADMIN-001")


# ── Case Detail Access Control ─────────────────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestManagerCaseDetailAccessControl(_ManagerDashboardTestBase):
    """Access control for manager case detail view."""

    def test_manager_can_access_case_detail(self) -> None:
        """Manager user can access the case detail page."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

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

        response = self.client.get(f"/manager/cases/{case_id}/")

        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_case_detail(self) -> None:
        """Admin user can access the case detail page."""
        self._set_env_database_url()
        self.client.login(username="admin@example.com", password="testpass123")

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

        response = self.client.get(f"/manager/cases/{case_id}/")

        self.assertEqual(response.status_code, 200)

    def test_case_detail_rejects_nir_role(self) -> None:
        """NIR role receives 403 Forbidden on manager case detail."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        case_id = uuid4()
        response = self.client.get(f"/manager/cases/{case_id}/")

        self.assertEqual(response.status_code, 403)

    def test_case_detail_rejects_doctor_role(self) -> None:
        """Doctor role receives 403 Forbidden on manager case detail."""
        self._set_env_database_url()
        self.client.login(username="doctor@example.com", password="testpass123")

        case_id = uuid4()
        response = self.client.get(f"/manager/cases/{case_id}/")

        self.assertEqual(response.status_code, 403)

    def test_case_detail_rejects_scheduler_role(self) -> None:
        """Scheduler role receives 403 Forbidden on manager case detail."""
        self._set_env_database_url()
        self.client.login(username="scheduler@example.com", password="testpass123")

        case_id = uuid4()
        response = self.client.get(f"/manager/cases/{case_id}/")

        self.assertEqual(response.status_code, 403)

    def test_case_detail_requires_authentication(self) -> None:
        """Anonymous users are redirected to login."""
        case_id = uuid4()
        response = self.client.get(f"/manager/cases/{case_id}/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_case_detail_returns_404_for_nonexistent_case(self) -> None:
        """Requesting a non-existent case returns 404."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

        nonexistent_id = uuid4()
        response = self.client.get(f"/manager/cases/{nonexistent_id}/")

        self.assertEqual(response.status_code, 404)


# ── Case Detail Content ────────────────────────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestManagerCaseDetailContent(_ManagerDashboardTestBase):
    """Manager case detail shows consolidated case information."""

    def test_case_detail_shows_case_id(self) -> None:
        """Case detail page shows the case id."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

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

        response = self.client.get(f"/manager/cases/{case_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(case_id))

    def test_case_detail_shows_status(self) -> None:
        """Case detail page shows the current status."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_APPT",
                updated_at=now,
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get(f"/manager/cases/{case_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WAIT_APPT")

    def test_case_detail_shows_patient_name(self) -> None:
        """Case detail page shows patient name."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_DOCTOR",
                updated_at=now,
                agency_record_number="REG-001",
                structured_data_json={
                    "patient": {"name": "João Silva", "age": 45},
                },
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get(f"/manager/cases/{case_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "João Silva")

    def test_case_detail_shows_record_number(self) -> None:
        """Case detail page shows agency record number."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_DOCTOR",
                updated_at=now,
                agency_record_number="2026-REC-001",
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get(f"/manager/cases/{case_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2026-REC-001")


# ── Case Detail Timeline (Auditability) ────────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestManagerCaseDetailTimeline(_ManagerDashboardTestBase):
    """Manager case detail preserves full audit timeline."""

    def test_case_detail_shows_timeline(self) -> None:
        """Case detail shows chronological timeline of events."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

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
            self._insert_matrix_transcript(
                conn,
                case_id=case_id.hex,
                event_id="$evt-timeline",
                captured_at=now,
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get(f"/manager/cases/{case_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Linha do Tempo")

    def test_case_detail_shows_matrix_events(self) -> None:
        """Timeline includes matrix message transcript events."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

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
            self._insert_matrix_transcript(
                conn,
                case_id=case_id.hex,
                event_id="$evt-matrix",
                message_type="room2_doctor_reply",
                captured_at=now,
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get(f"/manager/cases/{case_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "room2_doctor_reply")

    def test_case_detail_shows_web_events(self) -> None:
        """Timeline includes web human events."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

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
            self._insert_case_event(
                conn,
                case_id=case_id.hex,
                event_type="NIR_PDF_UPLOAD",
                actor_user_id="nir-1",
                payload='{"origin":"web","actor":"nir@example.com",'
                '"summary_text":"PDF uploaded via web"}',
                ts=now,
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get(f"/manager/cases/{case_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "NIR_PDF_UPLOAD")


# ── Case Detail Read-Only (No Admin Controls for Manager) ──────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestManagerCaseDetailReadOnly(_ManagerDashboardTestBase):
    """Manager case detail does not expose admin-only mutation controls."""

    def test_case_detail_no_acknowledge_button_for_manager(self) -> None:
        """Manager does not see the NIR acknowledge/finalize button."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_R1_CLEANUP_THUMBS",
                updated_at=now,
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get(f"/manager/cases/{case_id}/")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Manager should NOT see the acknowledge/finalize button
        self.assertNotIn("Confirmar Recebimento", content)
        self.assertNotIn("acknowledge", content.lower())

    def test_case_detail_no_mutation_actions_for_manager(self) -> None:
        """Manager detail view does not contain case-mutation forms."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

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

        response = self.client.get(f"/manager/cases/{case_id}/")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # No case mutation forms (acknowledge, decision, upload, confirmation)
        self.assertNotIn("acknowledge", content.lower())
        self.assertNotIn("Confirmar Recebimento", content)
        self.assertNotIn('action="/nir/', content.lower())
        self.assertNotIn('action="/doctor/', content.lower())
        self.assertNotIn('action="/scheduler/', content.lower())

    def test_case_detail_no_admin_controls_for_manager(self) -> None:
        """Manager detail view does not contain admin management links."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

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

        response = self.client.get(f"/manager/cases/{case_id}/")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # No admin-specific controls like user management, prompt management
        self.assertNotIn("/admin/users", content.lower())
        self.assertNotIn("/admin/prompts", content.lower())


# ── Case Detail Dashboard Link ─────────────────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestManagerCaseDetailNavigation(_ManagerDashboardTestBase):
    """Manager case detail includes navigation back to dashboard."""

    def test_case_detail_has_back_link_to_dashboard(self) -> None:
        """Case detail page has a link back to the manager dashboard."""
        self._set_env_database_url()
        self.client.login(username="manager@example.com", password="testpass123")

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

        response = self.client.get(f"/manager/cases/{case_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/manager/")
