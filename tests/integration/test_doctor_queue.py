"""Integration tests for the Doctor queue web page.

TDD tests for slice 3.1 — validates that:
- Cases in WAIT_DOCTOR status appear on the doctor queue page.
- Cases outside WAIT_DOCTOR do not appear.
- Only `doctor` role users can access the doctor queue.
- Authentication is required.
"""

from __future__ import annotations

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


class _DoctorQueueTestBase(TestCase):  # type: ignore[misc]
    """Base class with shared setup for doctor queue integration tests."""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up SQLAlchemy database with migrations for integration testing."""
        super().setUpClass()
        cls._tmp_dir = tempfile.mkdtemp()
        cls._db_path = Path(cls._tmp_dir) / "test_doctor_queue.sqlite"
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
        self.doctor_user = User.objects.create_user(
            email="doctor@example.com",
            password="testpass123",
            role="doctor",
        )
        self.nir_user = User.objects.create_user(
            email="nir@example.com",
            password="testpass123",
            role="nir",
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
    ) -> None:
        """Insert a case row for testing."""
        import json

        structured_json_str: str | None = None
        if structured_data_json is not None:
            structured_json_str = json.dumps(structured_data_json, ensure_ascii=False)

        connection.execute(
            sa.text(
                "INSERT INTO cases ("
                "case_id, status, origin_source, room1_origin_room_id, "
                "room1_origin_event_id, room1_sender_user_id, "
                "agency_record_number, structured_data_json, "
                "created_at, updated_at"
                ") VALUES ("
                ":case_id, :status, :origin_source, '!room1:example.org', "
                ":origin_event_id, '@nir:example.org', "
                ":agency_record_number, :structured_data_json, "
                ":created_at, :updated_at"
                ")"
            ),
            {
                "case_id": case_id,
                "status": status,
                "origin_source": origin_source,
                "origin_event_id": f"$origin-{case_id}",
                "agency_record_number": agency_record_number,
                "structured_data_json": structured_json_str,
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
        captured_at: datetime | None = None,
    ) -> None:
        """Insert a matrix message transcript for timeline/testing."""
        if captured_at is None:
            captured_at = datetime.now(tz=UTC)
        connection.execute(
            sa.text(
                "INSERT INTO case_matrix_message_transcripts ("
                "case_id, room_id, event_id, sender, sender_display_name, "
                "message_type, message_text, captured_at"
                ") VALUES ("
                ":case_id, '!room2:example.org', :event_id, '@doctor:example.org', "
                "'Dr. Carlos', 'room2_doctor_reply', 'ok', :captured_at"
                ")"
            ),
            {
                "case_id": case_id,
                "event_id": event_id,
                "captured_at": captured_at,
            },
        )


# ── Doctor Queue: Access Control ──────────────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestDoctorQueueAccessControl(_DoctorQueueTestBase):
    """Access control for the doctor queue page."""

    def test_doctor_queue_returns_200_for_doctor_user(self) -> None:
        """Doctor user can access the doctor queue page."""
        self._set_env_database_url()
        self.client.login(username="doctor@example.com", password="testpass123")

        response = self.client.get("/doctor/")

        self.assertEqual(response.status_code, 200)

    def test_doctor_queue_requires_authentication(self) -> None:
        """Anonymous users are redirected to login from doctor queue."""
        response = self.client.get("/doctor/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_doctor_queue_requires_doctor_role(self) -> None:
        """Non-doctor users receive 403 Forbidden on doctor queue."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        response = self.client.get("/doctor/")
        self.assertEqual(response.status_code, 403)


# ── Doctor Queue: Case Listing ────────────────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestDoctorQueueCaseListing(_DoctorQueueTestBase):
    """Doctor queue shows only cases awaiting medical decision."""

    def test_doctor_queue_shows_wait_doctor_cases(self) -> None:
        """Cases in WAIT_DOCTOR status appear in the doctor queue."""
        self._set_env_database_url()
        self.client.login(username="doctor@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_DOCTOR",
                updated_at=now,
                agency_record_number="REG-DOC-001",
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

        response = self.client.get("/doctor/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(case_id))

    def test_doctor_queue_excludes_non_wait_doctor_cases(self) -> None:
        """Cases not in WAIT_DOCTOR do not appear in the doctor queue."""
        self._set_env_database_url()
        self.client.login(username="doctor@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_APPT",
                updated_at=now,
                agency_record_number="REG-NON-DOC-001",
            )
            self._insert_matrix_transcript(
                conn,
                case_id=case_id.hex,
                event_id="$evt-wait-appt",
                captured_at=now,
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get("/doctor/")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, str(case_id))

    def test_doctor_queue_shows_only_wait_doctor_from_mixed_cases(self) -> None:
        """Only WAIT_DOCTOR cases appear when mixed with other statuses."""
        self._set_env_database_url()
        self.client.login(username="doctor@example.com", password="testpass123")

        doc_case_id = uuid4()
        non_doc_case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=doc_case_id.hex,
                status="WAIT_DOCTOR",
                updated_at=now,
                agency_record_number="REG-DOC-MIX-001",
            )
            self._insert_matrix_transcript(
                conn,
                case_id=doc_case_id.hex,
                event_id="$evt-mixed-doc",
                captured_at=now,
            )
            self._insert_case(
                conn,
                case_id=non_doc_case_id.hex,
                status="DOCTOR_ACCEPTED",
                updated_at=now - timedelta(hours=1),
                agency_record_number="REG-NON-DOC-MIX-001",
            )
            self._insert_matrix_transcript(
                conn,
                case_id=non_doc_case_id.hex,
                event_id="$evt-mixed-non-doc",
                captured_at=now - timedelta(hours=1),
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get("/doctor/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(doc_case_id))
        self.assertNotContains(response, str(non_doc_case_id))

    def test_doctor_queue_orders_by_latest_activity_desc(self) -> None:
        """Most recently active cases appear first in doctor queue."""
        self._set_env_database_url()
        self.client.login(username="doctor@example.com", password="testpass123")

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
                status="WAIT_DOCTOR",
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

        response = self.client.get("/doctor/")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        pos_newer = content.find(str(newer_id))
        pos_older = content.find(str(older_id))
        self.assertGreater(pos_newer, -1, "Newer case should be in response")
        self.assertGreater(pos_older, -1, "Older case should be in response")
        self.assertLess(pos_newer, pos_older, "Newer case should appear first")

    def test_doctor_queue_shows_patient_name_when_available(self) -> None:
        """Doctor queue shows patient name when available."""
        self._set_env_database_url()
        self.client.login(username="doctor@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_DOCTOR",
                updated_at=now,
                agency_record_number="REG-DOC-PATIENT",
                structured_data_json={
                    "patient": {"name": "João da Silva", "age": 62},
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

        response = self.client.get("/doctor/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "João da Silva")

    def test_doctor_queue_shows_record_number(self) -> None:
        """Doctor queue shows agency record number."""
        self._set_env_database_url()
        self.client.login(username="doctor@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_DOCTOR",
                updated_at=now,
                agency_record_number="2026-0502-001",
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

        response = self.client.get("/doctor/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2026-0502-001")

    def test_doctor_queue_shows_compact_summary(self) -> None:
        """Doctor queue shows operational compact summary per case."""
        self._set_env_database_url()
        self.client.login(username="doctor@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_DOCTOR",
                updated_at=now,
                agency_record_number="REG-DOC-SUMMARY",
            )
            self._insert_matrix_transcript(
                conn,
                case_id=case_id.hex,
                event_id="$evt-summary",
                captured_at=now,
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get("/doctor/")

        self.assertEqual(response.status_code, 200)
        # Should show operational status indicators
        self.assertContains(response, "AGUARDANDO")
