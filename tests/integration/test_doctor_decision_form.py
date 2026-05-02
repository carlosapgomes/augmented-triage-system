"""Integration tests for the Doctor decision form web page.

TDD tests for slice 3.2 — validates that:
- Doctor can submit accept decision with valid fields, progressing workflow.
- Doctor can submit deny decision with valid reason, following denial branch.
- Invalid payloads are rejected without mutating case state.
- Decision actions are auditable and chronologically visible.
- Form requires doctor role and authentication.
- Transitions only apply when case is in WAIT_DOCTOR status.
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


class _DoctorDecisionFormTestBase(TestCase):  # type: ignore[misc]
    """Base class with shared setup for doctor decision form integration tests."""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up SQLAlchemy database with migrations for integration testing."""
        super().setUpClass()
        cls._tmp_dir = tempfile.mkdtemp()
        cls._db_path = Path(cls._tmp_dir) / "test_doctor_decision_form.sqlite"
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


# ── Doctor Decision Form: Access Control ──────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestDoctorDecisionFormAccessControl(_DoctorDecisionFormTestBase):
    """Access control for the doctor decision form page."""

    def test_decision_form_requires_authentication(self) -> None:
        """Anonymous users are redirected to login from decision form."""
        case_id = uuid4()
        response = self.client.get(f"/doctor/cases/{case_id}/decision/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_decision_form_requires_doctor_role(self) -> None:
        """Non-doctor users receive 403 Forbidden on decision form."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        case_id = uuid4()
        response = self.client.get(f"/doctor/cases/{case_id}/decision/")
        self.assertEqual(response.status_code, 403)

    def test_decision_form_submit_requires_doctor_role(self) -> None:
        """Non-doctor users receive 403 Forbidden on decision submission."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        case_id = uuid4()
        response = self.client.post(
            f"/doctor/cases/{case_id}/decision/submit/",
            {"decision": "accept", "support_flag": "none", "admission_flow": "scheduled"},
        )
        self.assertEqual(response.status_code, 403)


# ── Doctor Decision Form: Accept Flow ─────────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestDoctorDecisionAcceptFlow(_DoctorDecisionFormTestBase):
    """Doctor acceptance with valid fields progresses to next branch."""

    def test_accept_scheduled_flow_transitions_case(self) -> None:
        """Accept with scheduled admission flow transitions to DOCTOR_ACCEPTED."""
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
                agency_record_number="REG-ACCEPT-001",
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.post(
            f"/doctor/cases/{case_id}/decision/submit/",
            {
                "decision": "accept",
                "support_flag": "none",
                "admission_flow": "scheduled",
            },
        )

        # Should redirect to doctor queue on success
        self.assertEqual(response.status_code, 302)
        self.assertIn("/doctor/", response.url)

        # Verify case transitioned
        conn2 = self._get_sync_connection()
        try:
            result = conn2.execute(
                sa.text(
                    "SELECT status, doctor_decision, doctor_user_id, "
                    "doctor_support_flag, doctor_admission_flow "
                    "FROM cases WHERE case_id = :case_id"
                ),
                {"case_id": case_id.hex},
            )
            row = result.fetchone()
            assert row is not None
            status, decision, doctor_user_id, support_flag, admission_flow = row
            self.assertEqual(status, "DOCTOR_ACCEPTED")
            self.assertEqual(decision, "accept")
            self.assertEqual(support_flag, "none")
            self.assertEqual(admission_flow, "scheduled")
        finally:
            conn2.close()

    def test_accept_scheduled_flow_enqueues_job(self) -> None:
        """Accept with scheduled flow enqueues post_room3_request job."""
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
                agency_record_number="REG-ACCEPT-JOB-001",
            )
            conn.commit()
        finally:
            conn.close()

        self.client.post(
            f"/doctor/cases/{case_id}/decision/submit/",
            {
                "decision": "accept",
                "support_flag": "none",
                "admission_flow": "scheduled",
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
            self.assertEqual(rows[0][0], "post_room3_request")
        finally:
            conn2.close()

    def test_accept_immediate_flow_transitions_and_enqueues_immediate_job(self) -> None:
        """Accept with immediate admission flow transitions and enqueues immediate job."""
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
                agency_record_number="REG-IMMEDIATE-001",
            )
            conn.commit()
        finally:
            conn.close()

        self.client.post(
            f"/doctor/cases/{case_id}/decision/submit/",
            {
                "decision": "accept",
                "support_flag": "anesthesist",
                "admission_flow": "immediate",
            },
        )

        conn2 = self._get_sync_connection()
        try:
            # Verify case transition
            result = conn2.execute(
                sa.text(
                    "SELECT status, doctor_admission_flow, doctor_support_flag "
                    "FROM cases WHERE case_id = :case_id"
                ),
                {"case_id": case_id.hex},
            )
            row = result.fetchone()
            assert row is not None
            status, admission_flow, support_flag = row
            self.assertEqual(status, "DOCTOR_ACCEPTED")
            self.assertEqual(admission_flow, "immediate")
            self.assertEqual(support_flag, "anesthesist")

            # Verify immediate job enqueued
            result2 = conn2.execute(
                sa.text(
                    "SELECT job_type FROM jobs "
                    "WHERE case_id = :case_id AND status = 'queued'"
                ),
                {"case_id": case_id.hex},
            )
            job_rows = result2.fetchall()
            self.assertEqual(len(job_rows), 1)
            self.assertEqual(job_rows[0][0], "post_immediate_admission_flow")
        finally:
            conn2.close()


# ── Doctor Decision Form: Deny Flow ───────────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestDoctorDecisionDenyFlow(_DoctorDecisionFormTestBase):
    """Doctor denial with valid reason follows denial branch."""

    def test_deny_with_reason_transitions_case(self) -> None:
        """Deny with reason transitions case to DOCTOR_DENIED."""
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
                agency_record_number="REG-DENY-001",
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.post(
            f"/doctor/cases/{case_id}/decision/submit/",
            {
                "decision": "deny",
                "support_flag": "none",
                "reason": "Paciente não preenche critérios clínicos",
            },
        )

        self.assertEqual(response.status_code, 302)

        conn2 = self._get_sync_connection()
        try:
            result = conn2.execute(
                sa.text(
                    "SELECT status, doctor_decision, doctor_reason "
                    "FROM cases WHERE case_id = :case_id"
                ),
                {"case_id": case_id.hex},
            )
            row = result.fetchone()
            assert row is not None
            status, decision, reason = row
            self.assertEqual(status, "DOCTOR_DENIED")
            self.assertEqual(decision, "deny")
            self.assertEqual(reason, "Paciente não preenche critérios clínicos")
        finally:
            conn2.close()

    def test_deny_enqueues_final_denial_job(self) -> None:
        """Deny enqueues post_room1_final_denial_triage job."""
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
                agency_record_number="REG-DENY-JOB-001",
            )
            conn.commit()
        finally:
            conn.close()

        self.client.post(
            f"/doctor/cases/{case_id}/decision/submit/",
            {
                "decision": "deny",
                "support_flag": "none",
                "reason": "Fora de escopo",
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
            self.assertEqual(rows[0][0], "post_room1_final_denial_triage")
        finally:
            conn2.close()

    def test_deny_without_reason_is_rejected(self) -> None:
        """Deny without reason is rejected with validation error."""
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
                agency_record_number="REG-DENY-NO-REASON-001",
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.post(
            f"/doctor/cases/{case_id}/decision/submit/",
            {
                "decision": "deny",
                "support_flag": "none",
                "reason": "",
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
                    "SELECT status, doctor_decision FROM cases WHERE case_id = :case_id"
                ),
                {"case_id": case_id.hex},
            )
            row = result.fetchone()
            assert row is not None
            self.assertEqual(row[0], "WAIT_DOCTOR")
            self.assertIsNone(row[1])
        finally:
            conn2.close()


# ── Doctor Decision Form: Validation & Audit ──────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestDoctorDecisionValidationAudit(_DoctorDecisionFormTestBase):
    """Invalid payload is rejected, action is auditable."""

    def test_invalid_decision_value_rejected(self) -> None:
        """Invalid decision value is rejected without mutation."""
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
                agency_record_number="REG-INVALID-DECISION-001",
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.post(
            f"/doctor/cases/{case_id}/decision/submit/",
            {"decision": "invalid_choice", "support_flag": "none"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "error")

        # Case state unchanged
        conn2 = self._get_sync_connection()
        try:
            result = conn2.execute(
                sa.text(
                    "SELECT status, doctor_decision FROM cases WHERE case_id = :case_id"
                ),
                {"case_id": case_id.hex},
            )
            row = result.fetchone()
            assert row is not None
            self.assertEqual(row[0], "WAIT_DOCTOR")
            self.assertIsNone(row[1])
        finally:
            conn2.close()

    def test_accept_without_admission_flow_rejected(self) -> None:
        """Accept without admission_flow is rejected."""
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
                agency_record_number="REG-NO-FLOW-001",
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.post(
            f"/doctor/cases/{case_id}/decision/submit/",
            {"decision": "accept", "support_flag": "none", "admission_flow": ""},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "error")

    def test_decision_creates_web_audit_event(self) -> None:
        """Decision submission creates a web human event audit entry."""
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
                agency_record_number="REG-AUDIT-001",
            )
            conn.commit()
        finally:
            conn.close()

        self.client.post(
            f"/doctor/cases/{case_id}/decision/submit/",
            {
                "decision": "accept",
                "support_flag": "anesthesist_icu",
                "admission_flow": "scheduled",
            },
        )

        conn2 = self._get_sync_connection()
        try:
            result = conn2.execute(
                sa.text(
                    "SELECT actor_type, event_type, actor_user_id, payload "
                    "FROM case_events "
                    "WHERE case_id = :case_id AND event_type = 'ROOM2_WIDGET_SUBMITTED'"
                ),
                {"case_id": case_id.hex},
            )
            rows = result.fetchall()
            self.assertGreaterEqual(len(rows), 1)
            actor_type, event_type, actor_user_id, payload = rows[0]
            self.assertEqual(actor_type, "system")
            self.assertEqual(event_type, "ROOM2_WIDGET_SUBMITTED")

            # Verify the web human event audit entry
            result2 = conn2.execute(
                sa.text(
                    "SELECT actor_type, event_type, actor_user_id, payload "
                    "FROM case_events "
                    "WHERE case_id = :case_id AND event_type = 'DOCTOR_DECISION'"
                ),
                {"case_id": case_id.hex},
            )
            web_rows = result2.fetchall()
            self.assertGreaterEqual(len(web_rows), 1)
            web_actor_type, web_event_type, web_actor_user_id, web_payload = web_rows[0]
            self.assertEqual(web_actor_type, "web_human")
            self.assertEqual(web_event_type, "DOCTOR_DECISION")
            self.assertIsNotNone(web_actor_user_id)
        finally:
            conn2.close()

    def test_decision_not_in_wait_doctor_rejected(self) -> None:
        """Submitting decision for case not in WAIT_DOCTOR is rejected."""
        self._set_env_database_url()
        self.client.login(username="doctor@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="DOCTOR_ACCEPTED",
                updated_at=now,
                agency_record_number="REG-WRONG-STATE-001",
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.post(
            f"/doctor/cases/{case_id}/decision/submit/",
            {
                "decision": "accept",
                "support_flag": "none",
                "admission_flow": "scheduled",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "error")

    def test_decision_non_existent_case(self) -> None:
        """Submitting decision for non-existent case shows error."""
        self._set_env_database_url()
        self.client.login(username="doctor@example.com", password="testpass123")

        case_id = uuid4()

        response = self.client.post(
            f"/doctor/cases/{case_id}/decision/submit/",
            {
                "decision": "accept",
                "support_flag": "none",
                "admission_flow": "scheduled",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "error")

    def test_decision_form_get_renders_for_doctor(self) -> None:
        """Doctor can see the decision form page."""
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
                agency_record_number="REG-GET-FORM-001",
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get(f"/doctor/cases/{case_id}/decision/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Decisão")
