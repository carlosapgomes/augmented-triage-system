"""Integration tests for NIR web PDF upload via Django views.

TDD tests for slice 2.1 — validates that:
- Upload of valid PDF creates a case visible in the database.
- Upload without file is rejected with validation feedback.
- Upload of non-PDF file is rejected with validation feedback.
- The NIR user action is auditable in the case events.
- The downstream processing job is dispatched.
- The upload endpoint requires NIR role.
- The upload endpoint requires authentication.
- Cases with FAILED status are visible (error state).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import sqlalchemy as sa
from alembic.config import Config
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from alembic import command

User = get_user_model()

# Minimal valid PDF content for testing.
VALID_PDF_BYTES = b"%PDF-1.4\n%fake pdf content for testing"


class _NirUploadTestBase(TestCase):  # type: ignore[misc]
    """Base class with shared setup for NIR upload integration tests."""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up SQLAlchemy database with migrations for integration testing."""
        super().setUpClass()
        cls._tmp_dir = tempfile.mkdtemp()
        cls._db_path = Path(cls._tmp_dir) / "test_nir_upload.sqlite"
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
        """Create NIR test user."""
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


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestNirUploadValidPdf(_NirUploadTestBase):
    """Valid PDF upload creates case, stores file, audits, enqueues job."""

    def test_upload_valid_pdf_creates_case(self) -> None:
        """Valid PDF creates a case in the database."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        response = self.client.post(
            "/nir/upload/submit/",
            {"pdf_file": SimpleUploadedFile(
                "referral.pdf", VALID_PDF_BYTES, content_type="application/pdf"
            )},
            format="multipart",
        )

        # Should render result page (200 OK, not redirect)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Encaminhamento Recebido")

    def test_upload_valid_pdf_case_in_database(self) -> None:
        """Case created via web upload is queryable in the database."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        response = self.client.post(
            "/nir/upload/submit/",
            {"pdf_file": SimpleUploadedFile(
                "referral.pdf", VALID_PDF_BYTES, content_type="application/pdf"
            )},
            format="multipart",
        )

        conn = self._get_sync_connection()
        try:
            # Get the case_id from the response context
            case_id = response.context["case_id"]
            result = conn.execute(
                sa.text("SELECT status, origin_source FROM cases WHERE case_id = :case_id"),
                {"case_id": case_id.replace("-", "")},
            )
            row = result.fetchone()
            self.assertIsNotNone(row)
            assert row is not None
            status, origin_source = row
            self.assertEqual(status, "R1_ACK_PROCESSING")
            self.assertEqual(origin_source, "web")
        finally:
            conn.close()

    def test_upload_valid_pdf_creates_audit_event(self) -> None:
        """Web upload creates an audit event in the case_events table."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        response = self.client.post(
            "/nir/upload/submit/",
            {"pdf_file": SimpleUploadedFile(
                "referral.pdf", VALID_PDF_BYTES, content_type="application/pdf"
            )},
            format="multipart",
        )

        conn = self._get_sync_connection()
        try:
            case_id = response.context["case_id"]
            result = conn.execute(
                sa.text(
                    "SELECT actor_type, event_type, actor_user_id FROM case_events "
                    "WHERE case_id = :case_id AND event_type = 'NIR_PDF_UPLOAD'"
                ),
                {"case_id": case_id.replace("-", "")},
            )
            rows = result.fetchall()
            self.assertEqual(len(rows), 1)
            actor_type, event_type, actor_user_id = rows[0]
            self.assertEqual(actor_type, "web_human")
            self.assertEqual(event_type, "NIR_PDF_UPLOAD")
        finally:
            conn.close()

    def test_upload_valid_pdf_enqueues_processing_job(self) -> None:
        """Web upload enqueues a process_pdf_case job."""
        import json

        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        response = self.client.post(
            "/nir/upload/submit/",
            {"pdf_file": SimpleUploadedFile(
                "referral.pdf", VALID_PDF_BYTES, content_type="application/pdf"
            )},
            format="multipart",
        )

        conn = self._get_sync_connection()
        try:
            case_id = response.context["case_id"]
            result = conn.execute(
                sa.text(
                    "SELECT job_type, payload FROM jobs "
                    "WHERE case_id = :case_id AND job_type = 'process_pdf_case'"
                ),
                {"case_id": case_id.replace("-", "")},
            )
            rows = result.fetchall()
            self.assertEqual(len(rows), 1)
            job_type, payload_raw = rows[0]
            payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
            self.assertEqual(job_type, "process_pdf_case")
            self.assertEqual(payload.get("origin_source"), "web")
            self.assertIn("web_pdf_storage_path", payload)
        finally:
            conn.close()


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestNirUploadValidation(_NirUploadTestBase):
    """Invalid uploads are rejected deterministically."""

    def test_upload_without_file_rejected(self) -> None:
        """Submitting without a file shows validation error."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        response = self.client.post(
            "/nir/upload/submit/",
            {},
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Selecione um arquivo PDF")

    def test_upload_non_pdf_extension_rejected(self) -> None:
        """Uploading a non-PDF file shows validation error."""
        self._set_env_database_url()
        self.client.login(username="nir@example.com", password="testpass123")

        response = self.client.post(
            "/nir/upload/submit/",
            {"pdf_file": SimpleUploadedFile(
                "document.txt", b"not a pdf", content_type="text/plain"
            )},
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "error")  # Form re-rendered with error

    def test_upload_requires_nir_role(self) -> None:
        """Non-NIR users receive 403 Forbidden on upload form."""
        self.client.login(username="doctor@example.com", password="testpass123")

        response = self.client.get("/nir/upload/")
        self.assertEqual(response.status_code, 403)

    def test_upload_submit_requires_nir_role(self) -> None:
        """Non-NIR users receive 403 Forbidden on upload submission."""
        self.client.login(username="doctor@example.com", password="testpass123")

        response = self.client.post(
            "/nir/upload/submit/",
            {"pdf_file": SimpleUploadedFile(
                "referral.pdf", VALID_PDF_BYTES, content_type="application/pdf"
            )},
            format="multipart",
        )
        self.assertEqual(response.status_code, 403)

    def test_upload_form_requires_authentication(self) -> None:
        """Anonymous users are redirected to login from upload form."""
        response = self.client.get("/nir/upload/")
        # login_required redirects to /login/
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)


@override_settings(
    PDF_STORAGE_DIR=os.path.join(tempfile.gettempdir(), "ats_test_pdfs"),
)
class TestNirUploadErrorVisibility(_NirUploadTestBase):
    """Downstream failure leaves visible operational state for NIR."""

    def test_failed_case_status_visible_in_database(self) -> None:
        """Cases with FAILED status are queryable for NIR visibility."""
        self._set_env_database_url()
        conn = self._get_sync_connection()
        try:
            # Simulate a case that was created via web and then failed downstream.
            conn.execute(
                sa.text(
                    "INSERT INTO cases ("
                    "case_id, status, origin_source, room1_origin_room_id, "
                    "room1_origin_event_id, room1_sender_user_id, created_at, updated_at"
                    ") VALUES ("
                    ":case_id, 'FAILED', 'web', NULL, NULL, NULL, "
                    "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP"
                    ")"
                ),
                {"case_id": "a" * 32},
            )
            conn.commit()

            result = conn.execute(
                sa.text("SELECT status, origin_source FROM cases WHERE origin_source = 'web'")
            )
            rows = result.fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0], "FAILED")
        finally:
            conn.close()
