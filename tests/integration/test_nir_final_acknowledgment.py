"""Integration tests for NIR final acknowledgment web flow.

TDD tests for slice 5.1 — validates that:
- Final result appears for NIR on case detail (acknowledgment button present).
- NIR can submit valid acknowledgment via web form.
- Valid acknowledgment is persisted in database (audit event, cleanup job).
- Repeat acknowledgment is idempotent (no duplicate effects).
- Wrong state cases do not show acknowledgment button.
- Nonexistent cases return 404.
- Non-NIR roles receive 403 Forbidden.
- Unauthenticated users are redirected to login.
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


class _NirAcknowledgmentTestBase(TestCase):  # type: ignore[misc]
    """Base class with shared setup for NIR acknowledgment integration tests."""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up SQLAlchemy database with migrations for integration testing."""
        super().setUpClass()
        cls._tmp_dir = tempfile.mkdtemp()
        cls._db_path = Path(cls._tmp_dir) / "test_nir_ack.sqlite"
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
        self.nir_user_id = str(self.nir_user.pk)

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
        updated_at: datetime | None = None,
        origin_source: str = "matrix",
        agency_record_number: str | None = None,
        structured_data_json: dict[str, object] | None = None,
        room1_final_reply_event_id: str | None = None,
        cleanup_triggered_at: datetime | None = None,
    ) -> None:
        """Insert a case row for testing."""
        if updated_at is None:
            updated_at = datetime.now(tz=UTC)
        connection.execute(
            sa.text(
                "INSERT INTO cases ("
                "case_id, status, origin_source, room1_origin_room_id, "
                "room1_origin_event_id, room1_sender_user_id, "
                "agency_record_number, structured_data_json, "
                "room1_final_reply_event_id, cleanup_triggered_at, "
                "created_at, updated_at"
                ") VALUES ("
                ":case_id, :status, :origin_source, '!room1:example.org', "
                ":origin_event_id, '@nir:example.org', "
                ":agency_record_number, :structured_data_json, "
                ":room1_final_reply_event_id, :cleanup_triggered_at, "
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
                "room1_final_reply_event_id": room1_final_reply_event_id,
                "cleanup_triggered_at": cleanup_triggered_at,
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
        message_type: str = "room1_final",
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
                ":case_id, '!room1:example.org', :event_id, '@bot:example.org', "
                "'ATS Bot', :message_type, 'Resultado final do caso.', :captured_at"
                ")"
            ),
            {
                "case_id": case_id,
                "event_id": event_id,
                "message_type": message_type,
                "captured_at": captured_at,
            },
        )


# ── Final result visibility ──────────────────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestFinalResultVisibility(_NirAcknowledgmentTestBase):
    """Final result appears for NIR with acknowledgment option."""

    def test_case_detail_shows_result_in_cleanup_thumbs_state(self) -> None:
        """Case in WAIT_R1_CLEANUP_THUMBS shows acknowledgment button."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_R1_CLEANUP_THUMBS",
                updated_at=now,
                room1_final_reply_event_id="$final-reply-1",
                agency_record_number="REG-ACK-001",
                structured_data_json={
                    "patient": {"name": "Carlos Silva", "age": 45},
                },
            )
            self._insert_matrix_transcript(
                conn,
                case_id=case_id.hex,
                event_id="$final-reply-1",
                captured_at=now,
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get(f"/nir/cases/{case_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(case_id))
        # The acknowledgment button/form should be present
        self.assertContains(response, "acknowledge")
        self.assertContains(response, "resultado")

    def test_case_detail_wrong_state_no_acknowledge_button(self) -> None:
        """Cases not in WAIT_R1_CLEANUP_THUMBS do not show acknowledgment."""
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
            conn.commit()
        finally:
            conn.close()

        response = self.client.get(f"/nir/cases/{case_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "acknowledge")

    def test_case_detail_already_cleaned_no_acknowledge_button(self) -> None:
        """Already CLEANED cases do not show acknowledgment."""
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
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get(f"/nir/cases/{case_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "acknowledge")


# ── Acknowledgment submission ─────────────────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestAcknowledgmentSubmission(_NirAcknowledgmentTestBase):
    """NIR submits valid acknowledgment via web form."""

    def test_valid_acknowledgment_redirects_to_dashboard(self) -> None:
        """Valid acknowledgment redirects to NIR dashboard."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_R1_CLEANUP_THUMBS",
                updated_at=now,
                room1_final_reply_event_id="$final-reply-2",
                agency_record_number="REG-ACK-002",
            )
            self._insert_matrix_transcript(
                conn,
                case_id=case_id.hex,
                event_id="$final-reply-2",
                captured_at=now,
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.post(f"/nir/cases/{case_id}/acknowledge/")

        # Should redirect to dashboard on success
        self.assertRedirects(response, "/nir/")

    def test_valid_acknowledgment_creates_audit_event(self) -> None:
        """Valid acknowledgment creates NIR_FINAL_ACKNOWLEDGMENT audit event."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_R1_CLEANUP_THUMBS",
                updated_at=now,
                room1_final_reply_event_id="$final-reply-3",
                agency_record_number="REG-ACK-003",
            )
            self._insert_matrix_transcript(
                conn,
                case_id=case_id.hex,
                event_id="$final-reply-3",
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.post(f"/nir/cases/{case_id}/acknowledge/")
        self.assertEqual(response.status_code, 302)

        conn = self._get_sync_connection()
        try:
            result = conn.execute(
                sa.text(
                    "SELECT event_type, actor_type, actor_user_id, payload "
                    "FROM case_events "
                    "WHERE case_id = :case_id AND event_type = 'NIR_FINAL_ACKNOWLEDGMENT'"
                ),
                {"case_id": case_id.hex},
            )
            rows = result.fetchall()
            self.assertEqual(len(rows), 1)
            event_type, actor_type, actor_user_id, payload_raw = rows[0]
            self.assertEqual(event_type, "NIR_FINAL_ACKNOWLEDGMENT")
            self.assertEqual(actor_type, "web_human")
            self.assertEqual(actor_user_id, self.nir_user_id)
            # Payload should contain origin and actor
            payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
            self.assertEqual(payload.get("origin"), "web")
            self.assertEqual(payload.get("actor"), "nir@example.com")
        finally:
            conn.close()

    def test_valid_acknowledgment_enqueues_cleanup_job(self) -> None:
        """Valid acknowledgment enqueues execute_cleanup job."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_R1_CLEANUP_THUMBS",
                updated_at=now,
                room1_final_reply_event_id="$final-reply-4",
            )
            self._insert_matrix_transcript(
                conn,
                case_id=case_id.hex,
                event_id="$final-reply-4",
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.post(f"/nir/cases/{case_id}/acknowledge/")
        self.assertEqual(response.status_code, 302)

        conn = self._get_sync_connection()
        try:
            result = conn.execute(
                sa.text(
                    "SELECT job_type FROM jobs "
                    "WHERE case_id = :case_id AND job_type = 'execute_cleanup'"
                ),
                {"case_id": case_id.hex},
            )
            rows = result.fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0], "execute_cleanup")
        finally:
            conn.close()

    def test_valid_acknowledgment_updates_cleanup_triggered_at(self) -> None:
        """Valid acknowledgment sets cleanup_triggered_at on the case."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_R1_CLEANUP_THUMBS",
                updated_at=now,
                room1_final_reply_event_id="$final-reply-5",
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.post(f"/nir/cases/{case_id}/acknowledge/")
        self.assertEqual(response.status_code, 302)

        conn = self._get_sync_connection()
        try:
            result = conn.execute(
                sa.text(
                    "SELECT cleanup_triggered_at, status FROM cases WHERE case_id = :case_id"
                ),
                {"case_id": case_id.hex},
            )
            row = result.fetchone()
            self.assertIsNotNone(row)
            assert row is not None
            self.assertIsNotNone(row[0], "cleanup_triggered_at should be set")
            self.assertIn(row[1], ("CLEANUP_RUNNING", "CLEANED"))
        finally:
            conn.close()


# ── Idempotency ──────────────────────────────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestAcknowledgmentIdempotency(_NirAcknowledgmentTestBase):
    """Repeat acknowledgment is idempotent."""

    def test_repeat_acknowledgment_returns_same_page(self) -> None:
        """Repeat acknowledgment after first success still handles gracefully."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_R1_CLEANUP_THUMBS",
                updated_at=now,
                room1_final_reply_event_id="$final-reply-6",
            )
            self._insert_matrix_transcript(
                conn,
                case_id=case_id.hex,
                event_id="$final-reply-6",
            )
            conn.commit()
        finally:
            conn.close()

        # First acknowledgment — should succeed
        response1 = self.client.post(f"/nir/cases/{case_id}/acknowledge/")
        self.assertEqual(response1.status_code, 302)

        # Second acknowledgment — should handle idempotently (redirect or error)
        response2 = self.client.post(f"/nir/cases/{case_id}/acknowledge/")
        # Should still work gracefully (redirect with possible error message)
        self.assertIn(response2.status_code, (302, 200))

    def test_repeat_acknowledgment_does_not_duplicate_jobs(self) -> None:
        """Repeat acknowledgment does not create duplicate cleanup jobs."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_R1_CLEANUP_THUMBS",
                updated_at=now,
                room1_final_reply_event_id="$final-reply-7",
            )
            conn.commit()
        finally:
            conn.close()

        # First ack
        self.client.post(f"/nir/cases/{case_id}/acknowledge/")

        # Second ack
        self.client.post(f"/nir/cases/{case_id}/acknowledge/")

        conn = self._get_sync_connection()
        try:
            result = conn.execute(
                sa.text(
                    "SELECT COUNT(*) FROM jobs "
                    "WHERE case_id = :case_id AND job_type = 'execute_cleanup'"
                ),
                {"case_id": case_id.hex},
            )
            row = result.fetchone()
            self.assertIsNotNone(row)
            count = row[0]  # type: ignore[index]
            self.assertEqual(count, 1, "Should only have one cleanup job")
        finally:
            conn.close()

    def test_repeat_acknowledgment_does_not_duplicate_audit_events(self) -> None:
        """Repeat acknowledgment does not create duplicate web human events."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        case_id = uuid4()
        now = datetime.now(tz=UTC)
        conn = self._get_sync_connection()
        try:
            self._insert_case(
                conn,
                case_id=case_id.hex,
                status="WAIT_R1_CLEANUP_THUMBS",
                updated_at=now,
                room1_final_reply_event_id="$final-reply-8",
            )
            conn.commit()
        finally:
            conn.close()

        # First ack
        self.client.post(f"/nir/cases/{case_id}/acknowledge/")

        # Second ack
        self.client.post(f"/nir/cases/{case_id}/acknowledge/")

        conn = self._get_sync_connection()
        try:
            result = conn.execute(
                sa.text(
                    "SELECT COUNT(*) FROM case_events "
                    "WHERE case_id = :case_id AND event_type = 'NIR_FINAL_ACKNOWLEDGMENT'"
                ),
                {"case_id": case_id.hex},
            )
            row = result.fetchone()
            self.assertIsNotNone(row)
            count = row[0]  # type: ignore[index]
            self.assertEqual(count, 1, "Should only have one acknowledgment event")
        finally:
            conn.close()


# ── Access control ───────────────────────────────────────────────────


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestAcknowledgmentAccessControl(_NirAcknowledgmentTestBase):
    """Access control for NIR acknowledgment endpoint."""

    def test_acknowledge_requires_authentication(self) -> None:
        """Anonymous users are redirected to login."""
        case_id = uuid4()
        response = self.client.post(f"/nir/cases/{case_id}/acknowledge/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_acknowledge_requires_nir_role(self) -> None:
        """Non-NIR users receive 403 Forbidden."""
        self._set_env_database_url()
        self.client.login(username="doctor@example.com", password="testpass123")

        case_id = uuid4()
        response = self.client.post(f"/nir/cases/{case_id}/acknowledge/")
        self.assertEqual(response.status_code, 403)

    def test_acknowledge_nonexistent_case_returns_404(self) -> None:
        """Acknowledgment of nonexistent case returns 404."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        nonexistent_id = uuid4()
        response = self.client.post(f"/nir/cases/{nonexistent_id}/acknowledge/")
        self.assertEqual(response.status_code, 404)

    def test_acknowledge_wrong_state_returns_400_or_redirect(self) -> None:
        """Acknowledgment of case in wrong state handles gracefully."""
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
            conn.commit()
        finally:
            conn.close()

        response = self.client.post(f"/nir/cases/{case_id}/acknowledge/")
        # Should handle gracefully — redirect or return error page
        self.assertIn(response.status_code, (200, 302, 400))
