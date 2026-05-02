"""Tests for intranet zone access guard middleware.

TDD tests for slice 3.2 — validates that:
- nir users inside the intranet CIDR are authorized.
- nir users outside the intranet CIDR are denied (403).
- scheduler users outside the intranet CIDR are denied (403).
- doctor, manager and admin users remain accessible outside the intranet.
- denied accesses leave auditable evidence in logs.
- valid credentials alone do not bypass the intranet policy.
"""

import ipaddress
import os
import tempfile
from pathlib import Path

from alembic.config import Config
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from alembic import command

User = get_user_model()

# The CIDR used for testing — 10.0.0.0/8 represents the intranet.
TEST_INTRANET_CIDRS: list[str] = ["10.0.0.0/8"]


def _is_in_intranet(ip: str, cidrs: list[str]) -> bool:
    """Check if an IP falls within any of the given CIDRs."""
    return any(
        ipaddress.ip_address(ip) in ipaddress.ip_network(cidr)
        for cidr in cidrs
    )


class TestNirIntranetAccess(TestCase):
    """Validate NIR access policy with IP-based zone enforcement."""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up SQLAlchemy database with migrations for NIR view tests."""
        super().setUpClass()
        cls._tmp_dir = tempfile.mkdtemp()
        cls._db_path = Path(cls._tmp_dir) / "test_intranet_nir.sqlite"
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
        """Create a NIR test user."""
        self.user = User.objects.create_user(
            email="nir@example.com",
            password="testpass123",
            role="nir",
        )

    @override_settings(INTRANET_CIDR_ALLOWLIST=TEST_INTRANET_CIDRS)
    def test_nir_inside_intranet_is_authorized(self) -> None:
        """NIR user accessing from an intranet IP must be allowed."""
        os.environ["DATABASE_URL"] = self._async_url
        self.client.login(username="nir@example.com", password="testpass123")
        response = self.client.get("/nir/", REMOTE_ADDR="10.0.1.50")
        assert response.status_code == 200

    @override_settings(INTRANET_CIDR_ALLOWLIST=TEST_INTRANET_CIDRS)
    def test_nir_outside_intranet_is_denied(self) -> None:
        """NIR user accessing from an external IP must be denied (403)."""
        self.client.login(username="nir@example.com", password="testpass123")
        response = self.client.get("/nir/", REMOTE_ADDR="203.0.113.50")
        assert response.status_code == 403

    @override_settings(INTRANET_CIDR_ALLOWLIST=TEST_INTRANET_CIDRS)
    def test_nir_valid_credentials_do_not_bypass_intranet(self) -> None:
        """Valid NIR credentials from outside intranet must still be denied."""
        self.client.login(username="nir@example.com", password="testpass123")
        # Even though session is valid, the IP check must deny
        response = self.client.get("/nir/", REMOTE_ADDR="198.51.100.10")
        assert response.status_code == 403


class TestSchedulerIntranetAccess(TestCase):
    """Validate Scheduler access policy with IP-based zone enforcement."""

    def setUp(self) -> None:
        """Create a Scheduler test user."""
        self.user = User.objects.create_user(
            email="scheduler@example.com",
            password="testpass123",
            role="scheduler",
        )

    @override_settings(INTRANET_CIDR_ALLOWLIST=TEST_INTRANET_CIDRS)
    def test_scheduler_inside_intranet_is_authorized(self) -> None:
        """Scheduler user accessing from an intranet IP must be allowed."""
        self.client.login(
            username="scheduler@example.com", password="testpass123"
        )
        response = self.client.get("/scheduler/", REMOTE_ADDR="10.0.2.30")
        assert response.status_code == 200

    @override_settings(INTRANET_CIDR_ALLOWLIST=TEST_INTRANET_CIDRS)
    def test_scheduler_outside_intranet_is_denied(self) -> None:
        """Scheduler user accessing from an external IP must be denied (403)."""
        self.client.login(
            username="scheduler@example.com", password="testpass123"
        )
        response = self.client.get("/scheduler/", REMOTE_ADDR="203.0.113.50")
        assert response.status_code == 403


class TestRemoteRolesAccessibleOutsideIntranet(TestCase):
    """Validate that doctor, manager, and admin remain reachable externally."""

    @override_settings(INTRANET_CIDR_ALLOWLIST=TEST_INTRANET_CIDRS)
    def test_doctor_outside_intranet_is_allowed(self) -> None:
        """Doctor user accessing from external IP must be allowed."""
        User.objects.create_user(
            email="doctor@example.com",
            password="testpass123",
            role="doctor",
        )
        self.client.login(username="doctor@example.com", password="testpass123")
        response = self.client.get("/doctor/", REMOTE_ADDR="203.0.113.50")
        assert response.status_code == 200

    @override_settings(INTRANET_CIDR_ALLOWLIST=TEST_INTRANET_CIDRS)
    def test_manager_outside_intranet_is_allowed(self) -> None:
        """Manager user accessing from external IP must be allowed."""
        User.objects.create_user(
            email="manager@example.com",
            password="testpass123",
            role="manager",
        )
        self.client.login(
            username="manager@example.com", password="testpass123"
        )
        response = self.client.get("/manager/", REMOTE_ADDR="203.0.113.50")
        assert response.status_code == 200

    @override_settings(INTRANET_CIDR_ALLOWLIST=TEST_INTRANET_CIDRS)
    def test_admin_outside_intranet_is_allowed(self) -> None:
        """Admin user accessing from external IP must be allowed."""
        User.objects.create_user(
            email="admin@example.com",
            password="testpass123",
            role="admin",
        )
        self.client.login(username="admin@example.com", password="testpass123")
        response = self.client.get("/admin/", REMOTE_ADDR="203.0.113.50")
        assert response.status_code == 200

    @override_settings(INTRANET_CIDR_ALLOWLIST=TEST_INTRANET_CIDRS)
    def test_doctor_inside_intranet_is_also_allowed(self) -> None:
        """Doctor user accessing from intranet IP must also be allowed."""
        User.objects.create_user(
            email="doctor@example.com",
            password="testpass123",
            role="doctor",
        )
        self.client.login(username="doctor@example.com", password="testpass123")
        response = self.client.get("/doctor/", REMOTE_ADDR="10.0.1.10")
        assert response.status_code == 200


class TestZoneDenialIsAuditable(TestCase):
    """Validate that zone denials leave auditable evidence."""

    def setUp(self) -> None:
        """Create a NIR test user."""
        self.user = User.objects.create_user(
            email="nir@example.com",
            password="testpass123",
            role="nir",
        )

    @override_settings(INTRANET_CIDR_ALLOWLIST=TEST_INTRANET_CIDRS)
    def test_denial_logs_audit_evidence(self) -> None:
        """Denied NIR access must produce a log entry with role and IP."""
        self.client.login(username="nir@example.com", password="testpass123")

        with self.assertLogs(
            "apps.django_ops.zone_guard", level="WARNING"
        ) as cm:
            response = self.client.get(
                "/nir/", REMOTE_ADDR="203.0.113.50"
            )
            assert response.status_code == 403

        # Must have at least one WARNING log
        assert len(cm.output) >= 1

        # Log must contain the role and IP for auditability
        log_message = cm.output[0]
        assert "nir" in log_message.lower()
        assert "203.0.113.50" in log_message

    @override_settings(INTRANET_CIDR_ALLOWLIST=TEST_INTRANET_CIDRS)
    def test_scheduler_denial_logs_audit_evidence(self) -> None:
        """Denied scheduler access must produce a log entry with role and IP."""
        User.objects.create_user(
            email="scheduler@example.com",
            password="testpass123",
            role="scheduler",
        )
        self.client.login(
            username="scheduler@example.com", password="testpass123"
        )

        with self.assertLogs(
            "apps.django_ops.zone_guard", level="WARNING"
        ) as cm:
            response = self.client.get(
                "/scheduler/", REMOTE_ADDR="198.51.100.10"
            )
            assert response.status_code == 403

        log_message = cm.output[0]
        assert "scheduler" in log_message.lower()
        assert "198.51.100.10" in log_message


class TestSmokeRouteBypassesZoneGuard(TestCase):
    """Validate that the smoke/health route is not affected by zone guard."""

    @override_settings(INTRANET_CIDR_ALLOWLIST=TEST_INTRANET_CIDRS)
    def test_smoke_route_accessible_from_any_ip(self) -> None:
        """The smoke endpoint must be accessible regardless of IP."""
        response = self.client.get("/smoke/", REMOTE_ADDR="203.0.113.50")
        assert response.status_code == 200


class TestLoginRouteBypassesZoneGuard(TestCase):
    """Validate that login route is not affected by zone guard."""

    @override_settings(INTRANET_CIDR_ALLOWLIST=TEST_INTRANET_CIDRS)
    def test_login_page_accessible_from_any_ip(self) -> None:
        """The login page must be accessible regardless of IP."""
        response = self.client.get("/login/", REMOTE_ADDR="203.0.113.50")
        assert response.status_code == 200
