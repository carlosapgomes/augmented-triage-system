"""Tests for login, logout, session and role-based redirect.

TDD tests for slice 2.2 — validates that:
- Valid credentials create an authenticated session.
- Invalid credentials return HTML error without session.
- Logout destroys the session.
- Each role is redirected to its dedicated landing route.
- Anonymous users accessing root are redirected to login.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class TestLoginSession(TestCase):
    """Validate login authentication and session creation."""

    def setUp(self) -> None:
        """Create a test user for login tests."""
        self.user = User.objects.create_user(
            email="nir@example.com",
            password="testpass123",
            role="nir",
        )

    def test_valid_login_creates_session(self) -> None:
        """Submitting valid credentials must create an authenticated session."""
        response = self.client.post(
            "/login/",
            {"username": "nir@example.com", "password": "testpass123"},
        )
        assert response.status_code == 302
        # Session must contain authentication data
        assert "_auth_user_id" in self.client.session
        assert int(self.client.session["_auth_user_id"]) == self.user.pk

    def test_valid_login_redirects_to_role_home(self) -> None:
        """After valid login, user is redirected to their role's landing page."""
        response = self.client.post(
            "/login/",
            {"username": "nir@example.com", "password": "testpass123"},
        )
        assert response.status_code == 302
        assert response.url == "/nir/"

    def test_invalid_login_returns_error_html(self) -> None:
        """Invalid credentials must return an HTML error response."""
        response = self.client.post(
            "/login/",
            {"username": "nir@example.com", "password": "wrongpass"},
        )
        assert response.status_code == 200
        assert b"error" in response.content.lower() or b"invalid" in response.content.lower()

    def test_invalid_login_does_not_create_session(self) -> None:
        """Invalid credentials must NOT create an authenticated session."""
        self.client.post(
            "/login/",
            {"username": "nir@example.com", "password": "wrongpass"},
        )
        assert "_auth_user_id" not in self.client.session

    def test_login_page_renders_form(self) -> None:
        """GET /login/ must render an HTML form with email and password fields."""
        response = self.client.get("/login/")
        assert response.status_code == 200
        content = response.content.decode()
        assert "email" in content.lower() or "username" in content.lower()
        assert "password" in content.lower()


class TestLogoutSession(TestCase):
    """Validate logout destroys the session."""

    def setUp(self) -> None:
        """Create and authenticate a test user."""
        self.user = User.objects.create_user(
            email="doctor@example.com",
            password="testpass123",
            role="doctor",
        )
        self.client.login(username="doctor@example.com", password="testpass123")

    def test_logout_destroys_session(self) -> None:
        """Logging out must clear the authenticated session."""
        assert "_auth_user_id" in self.client.session
        response = self.client.get("/logout/")
        assert response.status_code == 302
        # After logout, session must no longer have auth user
        assert "_auth_user_id" not in self.client.session

    def test_logout_redirects_to_login(self) -> None:
        """After logout, user must be redirected to the login page."""
        response = self.client.get("/logout/")
        assert response.status_code == 302
        assert response.url == "/login/"


class TestRoleBasedRedirect(TestCase):
    """Validate each role redirects to its correct landing route."""

    def _create_and_login(self, role: str) -> None:
        """Helper to create a user with a given role and log in."""
        User.objects.create_user(
            email=f"{role}@example.com",
            password="testpass123",
            role=role,
        )

    def test_nir_redirects_to_nir_home(self) -> None:
        """NIR role must redirect to /nir/ after login."""
        self._create_and_login("nir")
        response = self.client.post(
            "/login/",
            {"username": "nir@example.com", "password": "testpass123"},
        )
        assert response.status_code == 302
        assert response.url == "/nir/"

    def test_doctor_redirects_to_doctor_home(self) -> None:
        """Doctor role must redirect to /doctor/ after login."""
        self._create_and_login("doctor")
        response = self.client.post(
            "/login/",
            {"username": "doctor@example.com", "password": "testpass123"},
        )
        assert response.status_code == 302
        assert response.url == "/doctor/"

    def test_scheduler_redirects_to_scheduler_home(self) -> None:
        """Scheduler role must redirect to /scheduler/ after login."""
        self._create_and_login("scheduler")
        response = self.client.post(
            "/login/",
            {"username": "scheduler@example.com", "password": "testpass123"},
        )
        assert response.status_code == 302
        assert response.url == "/scheduler/"

    def test_manager_redirects_to_manager_home(self) -> None:
        """Manager role must redirect to /manager/ after login."""
        self._create_and_login("manager")
        response = self.client.post(
            "/login/",
            {"username": "manager@example.com", "password": "testpass123"},
        )
        assert response.status_code == 302
        assert response.url == "/manager/"

    def test_admin_redirects_to_admin_home(self) -> None:
        """Admin role must redirect to /admin/ after login."""
        self._create_and_login("admin")
        response = self.client.post(
            "/login/",
            {"username": "admin@example.com", "password": "testpass123"},
        )
        assert response.status_code == 302
        assert response.url == "/admin/"


class TestRootRedirect(TestCase):
    """Validate anonymous user at root is redirected to login."""

    def test_anonymous_root_redirects_to_login(self) -> None:
        """Unauthenticated user requesting / must be redirected to /login/."""
        response = self.client.get("/")
        assert response.status_code == 302
        assert "/login/" in response.url


class TestRolePlaceholderPages(TestCase):
    """Validate role-specific placeholder pages are accessible when logged in."""

    def test_nir_page_accessible_when_authenticated(self) -> None:
        """Authenticated nir user can access /nir/ page."""
        User.objects.create_user(
            email="nir@example.com", password="testpass123", role="nir"
        )
        self.client.login(username="nir@example.com", password="testpass123")
        response = self.client.get("/nir/")
        assert response.status_code == 200

    def test_doctor_page_accessible_when_authenticated(self) -> None:
        """Authenticated doctor user can access /doctor/ page."""
        User.objects.create_user(
            email="doctor@example.com", password="testpass123", role="doctor"
        )
        self.client.login(username="doctor@example.com", password="testpass123")
        response = self.client.get("/doctor/")
        assert response.status_code == 200

    def test_scheduler_page_accessible_when_authenticated(self) -> None:
        """Authenticated scheduler user can access /scheduler/ page."""
        User.objects.create_user(
            email="scheduler@example.com", password="testpass123", role="scheduler"
        )
        self.client.login(username="scheduler@example.com", password="testpass123")
        response = self.client.get("/scheduler/")
        assert response.status_code == 200

    def test_manager_page_accessible_when_authenticated(self) -> None:
        """Authenticated manager user can access /manager/ page."""
        User.objects.create_user(
            email="manager@example.com", password="testpass123", role="manager"
        )
        self.client.login(username="manager@example.com", password="testpass123")
        response = self.client.get("/manager/")
        assert response.status_code == 200

    def test_admin_page_accessible_when_authenticated(self) -> None:
        """Authenticated admin user can access /admin/ page."""
        User.objects.create_user(
            email="admin@example.com", password="testpass123", role="admin"
        )
        self.client.login(username="admin@example.com", password="testpass123")
        response = self.client.get("/admin/")
        assert response.status_code == 200

    def test_role_page_requires_login(self) -> None:
        """Unauthenticated user accessing /nir/ is redirected to login."""
        response = self.client.get("/nir/")
        assert response.status_code == 302
        assert "/login/" in response.url
