"""Tests for the custom Django User model and Role enum.

Validates that the custom user model persists with supported roles,
rejects invalid roles, and enforces normalized/unique email addresses.
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.django_ops.models import Role, User


class TestRoleEnum(TestCase):
    """Validate the Role enum contains all five approved roles."""

    def test_role_has_nir(self) -> None:
        """The nir role must exist."""
        assert Role.NIR == "nir"

    def test_role_has_doctor(self) -> None:
        """The doctor role must exist."""
        assert Role.DOCTOR == "doctor"

    def test_role_has_scheduler(self) -> None:
        """The scheduler role must exist."""
        assert Role.SCHEDULER == "scheduler"

    def test_role_has_manager(self) -> None:
        """The manager role must exist."""
        assert Role.MANAGER == "manager"

    def test_role_has_admin(self) -> None:
        """The admin role must exist."""
        assert Role.ADMIN == "admin"

    def test_role_exactly_five_values(self) -> None:
        """Only the five approved roles must be present."""
        assert len(Role) == 5

    def test_role_choices_contains_all(self) -> None:
        """Role.choices must include all five roles."""
        values = {choice[0] for choice in Role.choices}
        assert values == {"nir", "doctor", "scheduler", "manager", "admin"}


class TestUserPersistence(TestCase):
    """Validate user creation and persistence with supported roles."""

    def test_create_user_with_nir_role(self) -> None:
        """A user with nir role must persist correctly."""
        user = User.objects.create_user(
            email="nir@example.com",
            password="testpass123",
            role=Role.NIR,
        )
        assert user.pk is not None
        assert user.role == Role.NIR
        assert user.email == "nir@example.com"

    def test_create_user_with_doctor_role(self) -> None:
        """A user with doctor role must persist correctly."""
        user = User.objects.create_user(
            email="doctor@example.com",
            password="testpass123",
            role=Role.DOCTOR,
        )
        assert user.pk is not None
        assert user.role == Role.DOCTOR

    def test_create_user_with_scheduler_role(self) -> None:
        """A user with scheduler role must persist correctly."""
        user = User.objects.create_user(
            email="scheduler@example.com",
            password="testpass123",
            role=Role.SCHEDULER,
        )
        assert user.pk is not None
        assert user.role == Role.SCHEDULER

    def test_create_user_with_manager_role(self) -> None:
        """A user with manager role must persist correctly."""
        user = User.objects.create_user(
            email="manager@example.com",
            password="testpass123",
            role=Role.MANAGER,
        )
        assert user.pk is not None
        assert user.role == Role.MANAGER

    def test_create_user_with_admin_role(self) -> None:
        """A user with admin role must persist correctly."""
        user = User.objects.create_user(
            email="admin@example.com",
            password="testpass123",
            role=Role.ADMIN,
        )
        assert user.pk is not None
        assert user.role == Role.ADMIN

    def test_created_user_is_active_by_default(self) -> None:
        """A newly created user must be active by default."""
        user = User.objects.create_user(
            email="active@example.com",
            password="testpass123",
            role=Role.DOCTOR,
        )
        assert user.is_active is True

    def test_created_user_is_not_staff_by_default(self) -> None:
        """A newly created user must not be staff by default."""
        user = User.objects.create_user(
            email="staff@example.com",
            password="testpass123",
            role=Role.DOCTOR,
        )
        assert user.is_staff is False

    def test_created_user_is_not_superuser_by_default(self) -> None:
        """A newly created user must not be superuser by default."""
        user = User.objects.create_user(
            email="super@example.com",
            password="testpass123",
            role=Role.DOCTOR,
        )
        assert user.is_superuser is False

    def test_user_password_is_hashed(self) -> None:
        """The user password must not be stored in plaintext."""
        user = User.objects.create_user(
            email="hashed@example.com",
            password="testpass123",
            role=Role.DOCTOR,
        )
        assert user.password != "testpass123"
        assert user.check_password("testpass123")

    def test_user_str_returns_email(self) -> None:
        """The string representation of a user must return the email."""
        user = User.objects.create_user(
            email="str@example.com",
            password="testpass123",
            role=Role.DOCTOR,
        )
        assert str(user) == "str@example.com"


class TestInvalidRoleRejection(TestCase):
    """Validate that invalid roles are rejected deterministically."""

    def test_invalid_role_raises_validation_error(self) -> None:
        """An invalid role value must raise a ValidationError."""
        user = User(
            email="invalid@example.com",
            role="hacker",
        )
        with pytest.raises(ValidationError):
            user.full_clean()

    def test_empty_role_raises_validation_error(self) -> None:
        """An empty role value must raise a ValidationError."""
        user = User(
            email="empty@example.com",
            role="",
        )
        with pytest.raises(ValidationError):
            user.full_clean()


class TestEmailNormalizationAndUniqueness(TestCase):
    """Validate email normalization and uniqueness constraints."""

    def test_email_is_normalized_on_creation(self) -> None:
        """Email domain part must be normalized (lowercased)."""
        user = User.objects.create_user(
            email="User@Example.COM",
            password="testpass123",
            role=Role.DOCTOR,
        )
        assert user.email == "User@example.com"

    def test_duplicate_email_raises_integrity_error(self) -> None:
        """Creating two users with the same email must raise IntegrityError."""
        User.objects.create_user(
            email="dup@example.com",
            password="testpass123",
            role=Role.DOCTOR,
        )
        with pytest.raises(IntegrityError):
            User.objects.create_user(
                email="dup@example.com",
                password="otherpass456",
                role=Role.MANAGER,
            )

    def test_duplicate_email_case_insensitive(self) -> None:
        """Email uniqueness must be case-insensitive for the domain."""
        User.objects.create_user(
            email="case@example.com",
            password="testpass123",
            role=Role.DOCTOR,
        )
        with pytest.raises(IntegrityError):
            User.objects.create_user(
                email="case@EXAMPLE.COM",
                password="otherpass456",
                role=Role.MANAGER,
            )


class TestUsernameFieldIsEmail(TestCase):
    """Validate that USERNAME_FIELD is set to email."""

    def test_username_field_is_email(self) -> None:
        """The USERNAME_FIELD must be 'email'."""
        assert User.USERNAME_FIELD == "email"

    def test_required_fields_contains_role(self) -> None:
        """REQUIRED_FIELDS must include 'role'."""
        assert "role" in User.REQUIRED_FIELDS
