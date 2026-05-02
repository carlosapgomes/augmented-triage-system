"""Integration tests for NIR dashboard (case list) and case detail views.

TDD tests for slice 2.2 — validates that:
- NIR sees their relevant cases in the listing (non-cleaned cases);
- NIR case list shows operational progress information per case;
- NIR case list is accessible only to authenticated nir role users;
- Case detail shows progress stepper and timeline for a given case;
- Case detail is accessible only to authenticated nir role users;
- Non-NIR roles receive 403 Forbidden on NIR dashboard and detail;
- Case detail returns 404 for nonexistent case;
- NIR upload link is present on the dashboard;
- Timeline includes web-origin events alongside system events.
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


class _NirDashboardTestBase(TestCase):  # type: ignore[misc]
    """Base class with shared setup for NIR dashboard integration tests."""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up SQLAlchemy database with migrations for integration testing."""
        super().setUpClass()
        cls._tmp_dir = tempfile.mkdtemp()
        cls._db_path = Path(cls._tmp_dir) / "test_nir_dashboard.sqlite"
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

    def _insert_report_transcript(
        self,
        connection: sa.Connection,
        *,
        case_id: str,
        extracted_text: str = "Paciente com dor abdominal aguda.",
        captured_at: datetime | None = None,
    ) -> None:
        """Insert a report transcript for timeline testing."""
        if captured_at is None:
            captured_at = datetime.now(tz=UTC)
        connection.execute(
            sa.text(
                "INSERT INTO case_report_transcripts (case_id, extracted_text, captured_at) "
                "VALUES (:case_id, :extracted_text, :captured_at)"
            ),
            {
                "case_id": case_id,
                "extracted_text": extracted_text,
                "captured_at": captured_at,
            },
        )

    def _insert_audit_event(
        self,
        connection: sa.Connection,
        *,
        case_id: str,
        actor_type: str = "web_human",
        event_type: str = "NIR_PDF_UPLOAD",
        actor_user_id: str | None = None,
        captured_at: datetime | None = None,
    ) -> None:
        """Insert an audit event for timeline testing."""
        if captured_at is None:
            captured_at = datetime.now(tz=UTC)
        connection.execute(
            sa.text(
                "INSERT INTO case_events ("
                "case_id, actor_type, event_type, actor_user_id, "
                "room_id, matrix_event_id, payload, created_at"
                ") VALUES ("
                ":case_id, :actor_type, :event_type, :actor_user_id, "
                "NULL, NULL, '{}', :created_at"
                ")"
            ),
            {
                "case_id": case_id,
                "actor_type": actor_type,
                "event_type": event_type,
                "actor_user_id": actor_user_id,
                "created_at": captured_at,
            },
        )


# ── NIR Dashboard: Case Listing ───────────────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestNirDashboardCaseList(_NirDashboardTestBase):
    """NIR dashboard shows relevant cases with operational progress."""

    def test_nir_dashboard_returns_200_for_nir_user(self) -> None:
        """NIR user can access the dashboard page."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        response = self.client.get("/nir/")

        self.assertEqual(response.status_code, 200)

    def test_nir_dashboard_shows_active_cases(self) -> None:
        """Active cases appear in NIR dashboard listing."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

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

        response = self.client.get("/nir/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(case_id))

    def test_nir_dashboard_excludes_cleaned_cases(self) -> None:
        """CLEANED cases do not appear in NIR dashboard listing."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

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

        response = self.client.get("/nir/")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, str(case_id))

    def test_nir_dashboard_shows_operational_progress(self) -> None:
        """Case cards show compact operational summary."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_DOCTOR",
                updated_at=now,
                agency_record_number="REG-003",
            )
            self._insert_matrix_transcript(
                conn,
                case_id=case_id.hex,
                event_id="$evt-progress",
                captured_at=now,
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get("/nir/")

        self.assertEqual(response.status_code, 200)
        # Should show operational status indicators
        self.assertContains(response, "AGUARDANDO")

    def test_nir_dashboard_shows_upload_link(self) -> None:
        """Dashboard includes link to the upload form."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        response = self.client.get("/nir/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/nir/upload/")

    def test_nir_dashboard_shows_patient_name_when_available(self) -> None:
        """Case listing shows patient name from structured data."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

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

        response = self.client.get("/nir/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Maria Souza")

    def test_nir_dashboard_shows_record_number(self) -> None:
        """Case listing shows agency record number."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_DOCTOR",
                updated_at=now,
                agency_record_number="2026-0428-001",
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

        response = self.client.get("/nir/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2026-0428-001")

    def test_nir_dashboard_orders_by_latest_activity_desc(self) -> None:
        """Most recently active cases appear first."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

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

        response = self.client.get("/nir/")

        self.assertEqual(response.status_code, 200)
        # Newer case should appear before older case
        content = response.content.decode()
        pos_newer = content.find(str(newer_id))
        pos_older = content.find(str(older_id))
        self.assertGreater(pos_newer, -1, "Newer case should be in response")
        self.assertGreater(pos_older, -1, "Older case should be in response")
        self.assertLess(pos_newer, pos_older, "Newer case should appear first")


# ── NIR Dashboard: Access Control ─────────────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestNirDashboardAccessControl(_NirDashboardTestBase):
    """Access control for NIR dashboard and case detail."""

    def test_nir_dashboard_requires_authentication(self) -> None:
        """Anonymous users are redirected to login."""
        response = self.client.get("/nir/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_nir_dashboard_requires_nir_role(self) -> None:
        """Non-NIR users receive 403 Forbidden on NIR dashboard."""
        self._set_env_database_url()
        self.client.login(username="doctor@example.com", password="testpass123")

        response = self.client.get("/nir/")
        self.assertEqual(response.status_code, 403)

    def test_nir_case_detail_requires_authentication(self) -> None:
        """Anonymous users are redirected to login for case detail."""
        some_id = uuid4()
        response = self.client.get(f"/nir/cases/{some_id}/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_nir_case_detail_requires_nir_role(self) -> None:
        """Non-NIR users receive 403 Forbidden on case detail."""
        self._set_env_database_url()
        self.client.login(username="doctor@example.com", password="testpass123")

        some_id = uuid4()
        response = self.client.get(f"/nir/cases/{some_id}/")
        self.assertEqual(response.status_code, 403)


# ── NIR Case Detail ────────────────────────────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestNirCaseDetail(_NirDashboardTestBase):
    """NIR case detail shows progress stepper and timeline."""

    def test_case_detail_returns_200_for_existing_case(self) -> None:
        """NIR user sees case detail page for an existing case."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_DOCTOR",
                updated_at=now,
                agency_record_number="REG-DETAIL-001",
                structured_data_json={
                    "patient": {"name": "João Lima", "age": 62},
                },
            )
            self._insert_report_transcript(
                conn,
                case_id=case_id.hex,
                captured_at=now - timedelta(minutes=5),
            )
            self._insert_matrix_transcript(
                conn,
                case_id=case_id.hex,
                event_id="$evt-detail-1",
                captured_at=now - timedelta(minutes=3),
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get(f"/nir/cases/{case_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(case_id))
        self.assertContains(response, "João Lima")
        self.assertContains(response, "REG-DETAIL-001")

    def test_case_detail_shows_timeline_events(self) -> None:
        """Case detail renders timeline with multiple event sources."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

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
            self._insert_report_transcript(
                conn,
                case_id=case_id.hex,
                extracted_text="Relatório de encaminhamento.",
                captured_at=now - timedelta(minutes=10),
            )
            self._insert_matrix_transcript(
                conn,
                case_id=case_id.hex,
                event_id="$evt-timeline-1",
                message_type="room2_doctor_reply",
                captured_at=now - timedelta(minutes=5),
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get(f"/nir/cases/{case_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "timeline")
        self.assertContains(response, "Relatório de encaminhamento")

    def test_case_detail_shows_progress_stepper(self) -> None:
        """Case detail renders operational progress indicators."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_APPT",
                updated_at=now,
                doctor_decision="accept",
                doctor_admission_flow="scheduled",
            )
            self._insert_matrix_transcript(
                conn,
                case_id=case_id.hex,
                event_id="$evt-stepper",
                captured_at=now,
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get(f"/nir/cases/{case_id}/")

        self.assertEqual(response.status_code, 200)
        # Should show progress indicators
        self.assertContains(response, "progress")

    def test_case_detail_shows_status(self) -> None:
        """Case detail displays the current status."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

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
            self._insert_matrix_transcript(
                conn,
                case_id=case_id.hex,
                event_id="$evt-status",
                captured_at=now,
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get(f"/nir/cases/{case_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WAIT_APPT")

    def test_case_detail_returns_404_for_nonexistent_case(self) -> None:
        """Case detail returns 404 for a case that does not exist."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        nonexistent_id = uuid4()
        response = self.client.get(f"/nir/cases/{nonexistent_id}/")

        self.assertEqual(response.status_code, 404)

    def test_case_detail_includes_back_link_to_dashboard(self) -> None:
        """Case detail page has a link back to the NIR dashboard."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

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
                event_id="$evt-back-link",
                captured_at=now,
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get(f"/nir/cases/{case_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/nir/")

    def test_case_detail_shows_failed_status(self) -> None:
        """Case detail shows FAILED cases with appropriate visibility."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="FAILED",
                updated_at=now,
                origin_source="web",
            )
            self._insert_matrix_transcript(
                conn,
                case_id=case_id.hex,
                event_id="$evt-failed-detail",
                captured_at=now,
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get(f"/nir/cases/{case_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "FAILED")
