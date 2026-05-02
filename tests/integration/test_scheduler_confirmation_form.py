"""Integration tests for the Scheduler confirmation form web page.

TDD tests for slice 4.2 — validates that:
- Scheduler can confirm appointment with valid date, time, location, instructions.
- Scheduler can deny appointment with valid reason, following denial branch.
- Invalid payloads are rejected without mutating case state.
- Confirmation/denial actions are auditable.
- Form requires scheduler role and authentication.
- Transitions only apply when case is in WAIT_APPT status.
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


class _SchedulerConfirmationFormTestBase(TestCase):  # type: ignore[misc]
    """Base class with shared setup for scheduler confirmation form integration tests."""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up SQLAlchemy database with migrations for integration testing."""
        super().setUpClass()
        cls._tmp_dir = tempfile.mkdtemp()
        cls._db_path = Path(cls._tmp_dir) / "test_scheduler_conf_form.sqlite"
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

    def _insert_audit_event(
        self,
        connection: sa.Connection,
        *,
        case_id: str,
        event_type: str,
        actor_type: str,
        actor_user_id: str | None = None,
    ) -> None:
        """Insert an audit event for timeline testing."""
        connection.execute(
            sa.text(
                "INSERT INTO case_events ("
                "case_id, actor_type, event_type, actor_user_id, payload, created_at"
                ") VALUES ("
                ":case_id, :actor_type, :event_type, :actor_user_id, '{}', CURRENT_TIMESTAMP"
                ")"
            ),
            {
                "case_id": case_id,
                "actor_type": actor_type,
                "event_type": event_type,
                "actor_user_id": actor_user_id,
            },
        )


# ── Scheduler Confirmation Form: Access Control ───────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestSchedulerConfirmationFormAccessControl(_SchedulerConfirmationFormTestBase):
    """Access control for the scheduler confirmation form page."""

    def test_confirmation_form_requires_authentication(self) -> None:
        """Anonymous users are redirected to login from confirmation form."""
        case_id = uuid4()
        response = self.client.get(f"/scheduler/cases/{case_id}/confirm/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_confirmation_form_requires_scheduler_role(self) -> None:
        """Non-scheduler users receive 403 Forbidden on confirmation form."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        case_id = uuid4()
        response = self.client.get(f"/scheduler/cases/{case_id}/confirm/")
        self.assertEqual(response.status_code, 403)

    def test_confirmation_form_submit_requires_scheduler_role(self) -> None:
        """Non-scheduler users receive 403 Forbidden on form submission."""
        self._set_env_database_url()
        self.client.login(username="doctor@example.com", password="testpass123")

        case_id = uuid4()
        response = self.client.post(
            f"/scheduler/cases/{case_id}/confirm/submit/",
            {
                "action": "confirm",
                "appointment_date": "15/12/2026",
                "appointment_time": "14:30",
                "location": "Hospital Central - Ala B",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_confirmation_form_get_renders_for_scheduler(self) -> None:
        """Scheduler can see the confirmation form page."""
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
                agency_record_number="REG-GET-FORM-001",
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get(f"/scheduler/cases/{case_id}/confirm/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Confirmação")

    def test_confirmation_form_shows_case_data(self) -> None:
        """Confirmation form displays patient name and record number."""
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
                agency_record_number="REG-FORM-DATA",
                structured_data_json={
                    "patient": {"name": "Carlos Silva", "age": 52},
                },
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get(f"/scheduler/cases/{case_id}/confirm/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Carlos Silva")
        self.assertContains(response, "REG-FORM-DATA")


# ── Scheduler Confirmation Form: Confirm Flow ─────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestSchedulerConfirmationConfirmFlow(_SchedulerConfirmationFormTestBase):
    """Scheduler confirms appointment with valid fields, progressing workflow."""

    def test_confirm_with_date_time_location_transitions_case(self) -> None:
        """Confirm with date, time, and location transitions to APPT_CONFIRMED."""
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
                agency_record_number="REG-CONFIRM-001",
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.post(
            f"/scheduler/cases/{case_id}/confirm/submit/",
            {
                "action": "confirm",
                "appointment_date": "15/12/2026",
                "appointment_time": "14:30",
                "location": "Hospital Central - Ala B",
                "instructions": "Jejum 8h. Trazer documentos.",
            },
        )

        # Should redirect to scheduler queue on success
        self.assertEqual(response.status_code, 302)
        self.assertIn("/scheduler/", response.url)

        # Verify case transitioned
        conn2 = self._get_sync_connection()
        try:
            result = conn2.execute(
                sa.text(
                    "SELECT status, appointment_status, appointment_location, "
                    "appointment_instructions, scheduler_user_id "
                    "FROM cases WHERE case_id = :case_id"
                ),
                {"case_id": case_id.hex},
            )
            row = result.fetchone()
            assert row is not None
            status, appt_status, location, instructions, scheduler_user = row
            self.assertEqual(status, "APPT_CONFIRMED")
            self.assertEqual(appt_status, "confirmed")
            self.assertEqual(location, "Hospital Central - Ala B")
            self.assertEqual(instructions, "Jejum 8h. Trazer documentos.")
            self.assertIsNotNone(scheduler_user)
        finally:
            conn2.close()

    def test_confirm_without_instructions_still_succeeds(self) -> None:
        """Confirm without instructions (optional field) still works."""
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
                agency_record_number="REG-OPTIONAL-001",
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.post(
            f"/scheduler/cases/{case_id}/confirm/submit/",
            {
                "action": "confirm",
                "appointment_date": "20/01/2027",
                "appointment_time": "09:00",
                "location": "Consultório 3",
            },
        )

        self.assertEqual(response.status_code, 302)

        conn2 = self._get_sync_connection()
        try:
            result = conn2.execute(
                sa.text(
                    "SELECT status, appointment_status FROM cases WHERE case_id = :case_id"
                ),
                {"case_id": case_id.hex},
            )
            row = result.fetchone()
            assert row is not None
            self.assertEqual(row[0], "APPT_CONFIRMED")
            self.assertEqual(row[1], "confirmed")
        finally:
            conn2.close()

    def test_confirm_enqueues_post_room1_final_appt_job(self) -> None:
        """Confirm enqueues the post_room1_final_appt downstream job."""
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
                agency_record_number="REG-CONFIRM-JOB-001",
            )
            conn.commit()
        finally:
            conn.close()

        self.client.post(
            f"/scheduler/cases/{case_id}/confirm/submit/",
            {
                "action": "confirm",
                "appointment_date": "01/03/2027",
                "appointment_time": "11:00",
                "location": "Sala de Exames",
            },
        )

        conn2 = self._get_sync_connection()
        try:
            result = conn2.execute(
                sa.text(
                    "SELECT job_type FROM jobs "
                    "WHERE case_id = :case_id AND status = 'queued'"
                ),
                {"case_id": case_id.hex},
            )
            rows = result.fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0], "post_room1_final_appt")
        finally:
            conn2.close()


# ── Scheduler Confirmation Form: Deny Flow ────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestSchedulerConfirmationDenyFlow(_SchedulerConfirmationFormTestBase):
    """Scheduler denies appointment with valid reason, following denial branch."""

    def test_deny_with_reason_transitions_case(self) -> None:
        """Deny with reason transitions case to APPT_DENIED."""
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
                agency_record_number="REG-DENY-001",
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.post(
            f"/scheduler/cases/{case_id}/confirm/submit/",
            {
                "action": "deny",
                "deny_reason": "Paciente desistiu do procedimento",
            },
        )

        self.assertEqual(response.status_code, 302)

        conn2 = self._get_sync_connection()
        try:
            result = conn2.execute(
                sa.text(
                    "SELECT status, appointment_status, appointment_reason "
                    "FROM cases WHERE case_id = :case_id"
                ),
                {"case_id": case_id.hex},
            )
            row = result.fetchone()
            assert row is not None
            status, appt_status, reason = row
            self.assertEqual(status, "APPT_DENIED")
            self.assertEqual(appt_status, "denied")
            self.assertEqual(reason, "Paciente desistiu do procedimento")
        finally:
            conn2.close()

    def test_deny_enqueues_post_room1_final_appt_denied_job(self) -> None:
        """Deny enqueues post_room1_final_appt_denied job."""
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
                agency_record_number="REG-DENY-JOB-001",
            )
            conn.commit()
        finally:
            conn.close()

        self.client.post(
            f"/scheduler/cases/{case_id}/confirm/submit/",
            {
                "action": "deny",
                "deny_reason": "Agenda lotada",
            },
        )

        conn2 = self._get_sync_connection()
        try:
            result = conn2.execute(
                sa.text(
                    "SELECT job_type FROM jobs "
                    "WHERE case_id = :case_id AND status = 'queued'"
                ),
                {"case_id": case_id.hex},
            )
            rows = result.fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0], "post_room1_final_appt_denied")
        finally:
            conn2.close()

    def test_deny_without_reason_is_rejected(self) -> None:
        """Deny without reason is rejected with validation error."""
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
                agency_record_number="REG-DENY-NO-REASON-001",
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.post(
            f"/scheduler/cases/{case_id}/confirm/submit/",
            {
                "action": "deny",
                "deny_reason": "",
            },
        )

        # Form re-rendered with error (no redirect)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "error")

        # Case state unchanged
        conn2 = self._get_sync_connection()
        try:
            result = conn2.execute(
                sa.text(
                    "SELECT status, appointment_status FROM cases WHERE case_id = :case_id"
                ),
                {"case_id": case_id.hex},
            )
            row = result.fetchone()
            assert row is not None
            self.assertEqual(row[0], "WAIT_APPT")
            self.assertIsNone(row[1])
        finally:
            conn2.close()


# ── Scheduler Confirmation Form: Validation ────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestSchedulerConfirmationValidation(_SchedulerConfirmationFormTestBase):
    """Invalid payload is rejected without mutation."""

    def test_invalid_action_value_rejected(self) -> None:
        """Invalid action value is rejected without mutation."""
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
                agency_record_number="REG-INVALID-ACTION-001",
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.post(
            f"/scheduler/cases/{case_id}/confirm/submit/",
            {"action": "invalid_choice"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "error")

        # Case state unchanged
        conn2 = self._get_sync_connection()
        try:
            result = conn2.execute(
                sa.text(
                    "SELECT status, appointment_status FROM cases WHERE case_id = :case_id"
                ),
                {"case_id": case_id.hex},
            )
            row = result.fetchone()
            assert row is not None
            self.assertEqual(row[0], "WAIT_APPT")
            self.assertIsNone(row[1])
        finally:
            conn2.close()

    def test_confirm_without_date_rejected(self) -> None:
        """Confirm without appointment_date is rejected."""
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
                agency_record_number="REG-NO-DATE-001",
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.post(
            f"/scheduler/cases/{case_id}/confirm/submit/",
            {
                "action": "confirm",
                "appointment_time": "14:30",
                "location": "Hospital Central",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "error")

    def test_confirm_without_time_rejected(self) -> None:
        """Confirm without appointment_time is rejected."""
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
                agency_record_number="REG-NO-TIME-001",
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.post(
            f"/scheduler/cases/{case_id}/confirm/submit/",
            {
                "action": "confirm",
                "appointment_date": "15/12/2026",
                "location": "Hospital Central",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "error")

    def test_confirm_without_location_rejected(self) -> None:
        """Confirm without location is rejected."""
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
                agency_record_number="REG-NO-LOCATION-001",
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.post(
            f"/scheduler/cases/{case_id}/confirm/submit/",
            {
                "action": "confirm",
                "appointment_date": "15/12/2026",
                "appointment_time": "14:30",
                "location": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "error")

    def test_confirm_with_invalid_date_format_rejected(self) -> None:
        """Confirm with invalid date format is rejected."""
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
                agency_record_number="REG-BAD-DATE-001",
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.post(
            f"/scheduler/cases/{case_id}/confirm/submit/",
            {
                "action": "confirm",
                "appointment_date": "not-a-date",
                "appointment_time": "14:30",
                "location": "Hospital Central",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "error")


# ── Scheduler Confirmation Form: Audit ────────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestSchedulerConfirmationAudit(_SchedulerConfirmationFormTestBase):
    """Scheduler action is auditable with web human event."""

    def test_confirmation_creates_web_audit_event(self) -> None:
        """Confirm submission creates a SCHEDULER_CONFIRMATION web human event."""
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
                agency_record_number="REG-AUDIT-001",
            )
            conn.commit()
        finally:
            conn.close()

        self.client.post(
            f"/scheduler/cases/{case_id}/confirm/submit/",
            {
                "action": "confirm",
                "appointment_date": "15/12/2026",
                "appointment_time": "14:30",
                "location": "Hospital Central",
            },
        )

        conn2 = self._get_sync_connection()
        try:
            result = conn2.execute(
                sa.text(
                    "SELECT actor_type, event_type, actor_user_id, payload "
                    "FROM case_events "
                    "WHERE case_id = :case_id AND event_type = 'SCHEDULER_CONFIRMATION'"
                ),
                {"case_id": case_id.hex},
            )
            rows = result.fetchall()
            self.assertGreaterEqual(len(rows), 1)
            actor_type, event_type, actor_user_id, payload = rows[0]
            self.assertEqual(actor_type, "web_human")
            self.assertEqual(event_type, "SCHEDULER_CONFIRMATION")
            self.assertIsNotNone(actor_user_id)
        finally:
            conn2.close()

    def test_denial_creates_web_audit_event(self) -> None:
        """Deny submission creates a SCHEDULER_CONFIRMATION web human event."""
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
                agency_record_number="REG-AUDIT-DENY-001",
            )
            conn.commit()
        finally:
            conn.close()

        self.client.post(
            f"/scheduler/cases/{case_id}/confirm/submit/",
            {
                "action": "deny",
                "deny_reason": "Paciente desistiu",
            },
        )

        conn2 = self._get_sync_connection()
        try:
            result = conn2.execute(
                sa.text(
                    "SELECT actor_type, event_type, actor_user_id "
                    "FROM case_events "
                    "WHERE case_id = :case_id AND event_type = 'SCHEDULER_CONFIRMATION'"
                ),
                {"case_id": case_id.hex},
            )
            rows = result.fetchall()
            self.assertGreaterEqual(len(rows), 1)
            actor_type, event_type, actor_user_id = rows[0]
            self.assertEqual(actor_type, "web_human")
            self.assertEqual(event_type, "SCHEDULER_CONFIRMATION")
            self.assertIsNotNone(actor_user_id)
        finally:
            conn2.close()


# ── Scheduler Confirmation Form: Edge Cases ───────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestSchedulerConfirmationEdgeCases(_SchedulerConfirmationFormTestBase):
    """Edge cases for the scheduler confirmation form."""

    def test_confirmation_not_in_wait_appt_rejected(self) -> None:
        """Submitting confirmation for case not in WAIT_APPT shows error."""
        self._set_env_database_url()
        self.client.login(username="scheduler@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="APPT_CONFIRMED",
                updated_at=now,
                agency_record_number="REG-WRONG-STATE-001",
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.post(
            f"/scheduler/cases/{case_id}/confirm/submit/",
            {
                "action": "confirm",
                "appointment_date": "15/12/2026",
                "appointment_time": "14:30",
                "location": "Hospital Central",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "error")

    def test_confirmation_non_existent_case(self) -> None:
        """Submitting confirmation for non-existent case shows error."""
        self._set_env_database_url()
        self.client.login(username="scheduler@example.com", password="testpass123")

        case_id = uuid4()

        response = self.client.post(
            f"/scheduler/cases/{case_id}/confirm/submit/",
            {
                "action": "confirm",
                "appointment_date": "15/12/2026",
                "appointment_time": "14:30",
                "location": "Hospital Central",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "error")

    def test_duplicate_confirmation_rejected(self) -> None:
        """Second confirmation for an already-processed case is rejected."""
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
                agency_record_number="REG-DUP-001",
            )
            conn.commit()
        finally:
            conn.close()

        # First submit succeeds
        response1 = self.client.post(
            f"/scheduler/cases/{case_id}/confirm/submit/",
            {
                "action": "confirm",
                "appointment_date": "10/06/2027",
                "appointment_time": "08:00",
                "location": "Sala 1",
            },
        )
        self.assertEqual(response1.status_code, 302)

        # Second submit is rejected (case no longer in WAIT_APPT)
        response2 = self.client.post(
            f"/scheduler/cases/{case_id}/confirm/submit/",
            {
                "action": "confirm",
                "appointment_date": "10/06/2027",
                "appointment_time": "08:00",
                "location": "Sala 1",
            },
        )

        self.assertEqual(response2.status_code, 200)
        self.assertContains(response2, "error")

    def test_confirmation_form_get_not_in_wait_appt_returns_404(self) -> None:
        """GET form for case not in WAIT_APPT returns 404."""
        self._set_env_database_url()
        self.client.login(username="scheduler@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="APPT_DENIED",
                updated_at=now,
                agency_record_number="REG-NOT-WAITING-001",
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get(f"/scheduler/cases/{case_id}/confirm/")
        self.assertEqual(response.status_code, 404)
