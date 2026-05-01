"""Custom User model and Role enum for the django_ops application.

Provides the identity foundation with individual accounts and five
operational roles: nir, doctor, scheduler, manager, admin.
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _


class Role(models.TextChoices):  # type: ignore[misc]
    """Operational roles for triage system users.

    Each person receives exactly one role determining their
    authorization level and navigation surface.
    """

    NIR = "nir", _("NIR")
    DOCTOR = "doctor", _("Doctor")
    SCHEDULER = "scheduler", _("Scheduler")
    MANAGER = "manager", _("Manager")
    ADMIN = "admin", _("Admin")


class UserManager(BaseUserManager["User"]):  # type: ignore[misc]
    """Manager for the custom User model.

    Handles user and superuser creation with email as the
    primary identifier instead of username.
    """

    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: object,
    ) -> "User":
        """Create and save a regular user with the given email and password.

        Args:
            email: The user's email address (normalized automatically).
            password: Optional plaintext password (hashed before storage).
            **extra_fields: Additional model fields (e.g. role).

        Returns:
            The newly created User instance.

        Raises:
            ValueError: If email is not provided.
        """
        if not email:
            msg = "The email field must be set."
            raise ValueError(msg)
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user  # type: ignore[no-any-return]

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: object,
    ) -> "User":
        """Create and save a superuser with the given email and password.

        Superusers have is_staff and is_superuser set to True.

        Args:
            email: The superuser's email address.
            password: Optional plaintext password.
            **extra_fields: Additional model fields.

        Returns:
            The newly created superuser User instance.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            msg = "Superuser must have is_staff=True."
            raise ValueError(msg)
        if extra_fields.get("is_superuser") is not True:
            msg = "Superuser must have is_superuser=True."
            raise ValueError(msg)

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):  # type: ignore[misc]
    """Custom user model for the triage operations web application.

    Uses email as the primary identifier and assigns each user
    exactly one operational role for authorization.
    """

    email = models.EmailField(
        _("email address"),
        unique=True,
        error_messages={
            "unique": _("A user with that email already exists."),
        },
    )
    role = models.CharField(
        _("role"),
        max_length=20,
        choices=Role.choices,
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
    )
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
    )
    created_at = models.DateTimeField(
        _("created at"),
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        _("updated at"),
        auto_now=True,
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = ["role"]

    class Meta:
        """Meta options for the User model."""

        verbose_name = _("user")
        verbose_name_plural = _("users")

    def __str__(self) -> str:
        """Return the user's email as string representation."""
        return self.email  # type: ignore[no-any-return]
