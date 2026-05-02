"""Integration tests for the Scheduler queue web page.

TDD tests for slice 4.1 — validates that:
- Cases in WAIT_APPT status appear on the scheduler queue page.
- Cases outside WAIT_APPT do not appear.
- Only `scheduler` role users can access the scheduler queue.
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


class _SchedulerQueueTestBase(TestCase):  # type: ignore[misc]
    """Base class with shared setup for scheduler queue integration tests."""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up SQLAlchemy database with migrations for integration testing."""
        super().setUpClass()
        cls._tmp_dir = tempfile.mkdtemp()
        cls._db_path = Path(cls._tmp_dir) / "test_scheduler_queue.sqlite"
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
        self.scheduler_user = User.objects.create_user(
            email="scheduler@example.com",
            password="testpass123",
            role="scheduler",
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
                ":case_id, '!room3:example.org', :event_id, '@scheduler:example.org', "
                "'Scheduler Example', 'room3_scheduler_reply', 'ok', :captured_at"
                ")"
            ),
            {
                "case_id": case_id,
                "event_id": event_id,
                "captured_at": captured_at,
            },
        )


# ── Scheduler Queue: Access Control ───────────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestSchedulerQueueAccessControl(_SchedulerQueueTestBase):
    """Access control for the scheduler queue page."""

    def test_scheduler_queue_returns_200_for_scheduler_user(self) -> None:
        """Scheduler user can access the scheduler queue page."""
        self._set_env_database_url()
        self.client.login(username="scheduler@example.com", password="testpass123")

        response = self.client.get("/scheduler/")

        self.assertEqual(response.status_code, 200)

    def test_scheduler_queue_requires_authentication(self) -> None:
        """Anonymous users are redirected to login from scheduler queue."""
        response = self.client.get("/scheduler/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_scheduler_queue_requires_scheduler_role(self) -> None:
        """Non-scheduler users receive 403 Forbidden on scheduler queue."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        response = self.client.get("/scheduler/")
        self.assertEqual(response.status_code, 403)

    def test_doctor_cannot_access_scheduler_queue(self) -> None:
        """Doctor role users receive 403 Forbidden on scheduler queue."""
        self._set_env_database_url()
        self.client.login(username="doctor@example.com", password="testpass123")

        response = self.client.get("/scheduler/")
        self.assertEqual(response.status_code, 403)


# ── Scheduler Queue: Case Listing ─────────────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestSchedulerQueueCaseListing(_SchedulerQueueTestBase):
    """Scheduler queue shows only cases awaiting scheduling confirmation."""

    def test_scheduler_queue_shows_wait_appt_cases(self) -> None:
        """Cases in WAIT_APPT status appear in the scheduler queue."""
        self._set_env_database_url()
        self.client.login(username="scheduler@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_APPT",
                updated_at=now,
                agency_record_number="REG-SCH-001",
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

        response = self.client.get("/scheduler/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(case_id))

    def test_scheduler_queue_excludes_non_wait_appt_cases(self) -> None:
        """Cases not in WAIT_APPT do not appear in the scheduler queue."""
        self._set_env_database_url()
        self.client.login(username="scheduler@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_DOCTOR",
                updated_at=now,
                agency_record_number="REG-NON-SCH-001",
            )
            self._insert_matrix_transcript(
                conn,
                case_id=case_id.hex,
                event_id="$evt-wait-doc",
                captured_at=now,
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get("/scheduler/")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, str(case_id))

    def test_scheduler_queue_shows_only_wait_appt_from_mixed_cases(self) -> None:
        """Only WAIT_APPT cases appear when mixed with other statuses."""
        self._set_env_database_url()
        self.client.login(username="scheduler@example.com", password="testpass123")

        appt_case_id = uuid4()
        non_appt_case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=appt_case_id.hex,
                status="WAIT_APPT",
                updated_at=now,
                agency_record_number="REG-SCH-MIX-001",
            )
            self._insert_matrix_transcript(
                conn,
                case_id=appt_case_id.hex,
                event_id="$evt-mixed-appt",
                captured_at=now,
            )
            self._insert_case(
                conn,
                case_id=non_appt_case_id.hex,
                status="APPT_CONFIRMED",
                updated_at=now - timedelta(hours=1),
                agency_record_number="REG-NON-SCH-MIX-001",
            )
            self._insert_matrix_transcript(
                conn,
                case_id=non_appt_case_id.hex,
                event_id="$evt-mixed-non-appt",
                captured_at=now - timedelta(hours=1),
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get("/scheduler/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(appt_case_id))
        self.assertNotContains(response, str(non_appt_case_id))

    def test_scheduler_queue_orders_by_latest_activity_desc(self) -> None:
        """Most recently active cases appear first in scheduler queue."""
        self._set_env_database_url()
        self.client.login(username="scheduler@example.com", password="testpass123")

        older_id = uuid4()
        newer_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=older_id.hex,
                status="WAIT_APPT",
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

        response = self.client.get("/scheduler/")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        pos_newer = content.find(str(newer_id))
        pos_older = content.find(str(older_id))
        self.assertGreater(pos_newer, -1, "Newer case should be in response")
        self.assertGreater(pos_older, -1, "Older case should be in response")
        self.assertLess(pos_newer, pos_older, "Newer case should appear first")

    def test_scheduler_queue_shows_patient_name_when_available(self) -> None:
        """Scheduler queue shows patient name when available."""
        self._set_env_database_url()
        self.client.login(username="scheduler@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_APPT",
                updated_at=now,
                agency_record_number="REG-SCH-PATIENT",
                structured_data_json={
                    "patient": {"name": "Maria Oliveira", "age": 45},
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

        response = self.client.get("/scheduler/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Maria Oliveira")

    def test_scheduler_queue_shows_record_number(self) -> None:
        """Scheduler queue shows agency record number."""
        self._set_env_database_url()
        self.client.login(username="scheduler@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_APPT",
                updated_at=now,
                agency_record_number="2026-0502-002",
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

        response = self.client.get("/scheduler/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2026-0502-002")

    def test_scheduler_queue_shows_compact_summary(self) -> None:
        """Scheduler queue shows operational compact summary per case."""
        self._set_env_database_url()
        self.client.login(username="scheduler@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_APPT",
                updated_at=now,
                agency_record_number="REG-SCH-SUMMARY",
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

        response = self.client.get("/scheduler/")

        self.assertEqual(response.status_code, 200)
        # Should show operational status indicators
        self.assertContains(response, "AGUARDANDO")
