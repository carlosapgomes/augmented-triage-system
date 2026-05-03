"""Application service for Django-backed user management.

Reuses the same business logic patterns as ``UserManagementService``
but operates on the Django User model while writing audit events to
the SQLAlchemy ``auth_events`` table.

The service is the single source of truth for the Django admin
user-management surface: create, role update, block, activate, and
removal actions flow through this service so the consolidated view
can delegate without embedding business logic in the adapter.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from django.contrib.auth import get_user_model

from triage_automation.application.ports.auth_event_repository_port import (
    AuthEventCreateInput,
    AuthEventRepositoryPort,
)

User = get_user_model()


# ── Domain errors (same semantics as UserManagementService) ──────────


class DjangoUserNotFoundError(LookupError):
    """Raised when a target Django user cannot be found."""


class DjangoSelfUserManagementError(PermissionError):
    """Raised when admin attempts to block/remove their own account via Django."""


class DjangoLastActiveAdminError(PermissionError):
    """Raised when operation would leave zero active Django admins."""


class DjangoUserManagementAuthorizationError(PermissionError):
    """Raised when actor is not an admin user."""


class DjangoInvalidRoleError(ValueError):
    """Raised when a create/update request specifies an unsupported role."""


class DjangoEmailAlreadyExistsError(ValueError):
    """Raised when create-user attempts to use an existing email."""


class DjangoInvalidEmailError(ValueError):
    """Raised when email is blank."""


class DjangoInvalidPasswordError(ValueError):
    """Raised when password is blank."""


# ── Input DTOs ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class DjangoUserItem:
    """Flat user representation for admin listing."""

    pk: int
    email: str
    role: str
    is_active: bool


@dataclass(frozen=True)
class DjangoCreateUserRequest:
    """Application-layer create-user payload for the Django surface."""

    email: str
    password: str
    role: str  # raw role value (may be "reader" → mapped to "manager")


# ── Legacy mapping ───────────────────────────────────────────────────

LEGACY_ROLE_TO_OPERATIONAL: dict[str, str] = {
    "reader": "manager",
}

SUPPORTED_OPERATIONAL_ROLES: frozenset[str] = frozenset(
    {"nir", "doctor", "scheduler", "manager", "admin"}
)


def _to_operational_role(raw_role: str) -> str:
    """Map legacy roles and normalize to the supported operational set.

    ``reader`` → ``manager`` (deterministic mapping).
    Unsupported roles raise ``DjangoInvalidRoleError``.
    """
    normalized = raw_role.strip().lower()
    mapped = LEGACY_ROLE_TO_OPERATIONAL.get(normalized, normalized)
    if mapped not in SUPPORTED_OPERATIONAL_ROLES:
        raise DjangoInvalidRoleError(f"unsupported role: {raw_role}")
    return mapped


# ── Service ──────────────────────────────────────────────────────────


class DjangoUserManagementService:
    """User management for the consolidated Django admin surface.

    Delegates persistence to Django's ORM and audit to the shared
    SQLAlchemy ``auth_events`` table (via ``AuthEventRepositoryPort``).
    """

    def __init__(
        self,
        *,
        auth_events: AuthEventRepositoryPort,
        sqlalchemy_session_factory: object,
    ) -> None:
        self._auth_events = auth_events
        self._sa_session_factory = sqlalchemy_session_factory

    # ── list ─────────────────────────────────────────────────────────

    def list_users(self) -> list[DjangoUserItem]:
        """Return deterministic user listing for admin pages."""

        return [
            DjangoUserItem(
                pk=user.pk,
                email=user.email,
                role=user.role,
                is_active=user.is_active,
            )
            for user in User.objects.order_by("email")
        ]

    # ── create ───────────────────────────────────────────────────────

    def create_user(
        self,
        *,
        actor: Any,  # Django User instance
        payload: DjangoCreateUserRequest,
    ) -> DjangoUserItem:
        """Create one user and persist a ``user_created`` audit event."""

        self._require_admin_actor(actor=actor)
        email = payload.email.strip().lower()
        if not email:
            raise DjangoInvalidEmailError()
        password = payload.password.strip()
        if not password:
            raise DjangoInvalidPasswordError()

        role_value = _to_operational_role(payload.role)

        if User.objects.filter(email__iexact=email).exists():
            raise DjangoEmailAlreadyExistsError()

        created = User.objects.create_user(
            email=email,
            password=password,
            role=role_value,
        )

        self._write_audit_event(
            actor=actor,
            event_type="user_created",
            target=created,
        )

        return DjangoUserItem(
            pk=created.pk,
            email=created.email,
            role=created.role,
            is_active=created.is_active,
        )

    # ── update_role ──────────────────────────────────────────────────

    def update_user_role(
        self,
        *,
        actor: Any,  # Django User instance
        target_pk: int,
        new_role: str,
    ) -> DjangoUserItem:
        """Change the role of an existing user."""

        self._require_admin_actor(actor=actor)
        role_value = _to_operational_role(new_role)

        target = self._get_user_or_raise(pk=target_pk)

        # Preserve last-active-admin invariant.
        if target.role == "admin" and role_value != "admin":
            active_admin_count = User.objects.filter(
                role="admin", is_active=True
            ).count()
            if active_admin_count <= 1:
                raise DjangoLastActiveAdminError()

        old_role = target.role
        target.role = role_value
        target.save(update_fields=["role", "updated_at"])

        self._write_audit_event(
            actor=actor,
            event_type="user_role_changed",
            target=target,
            extra={"old_role": old_role, "new_role": role_value},
        )

        return DjangoUserItem(
            pk=target.pk,
            email=target.email,
            role=target.role,
            is_active=target.is_active,
        )

    # ── block ────────────────────────────────────────────────────────

    def block_user(
        self,
        *,
        actor: Any,  # Django User instance
        target_pk: int,
    ) -> DjangoUserItem:
        """Transition a user to blocked (is_active=False)."""

        self._require_admin_actor(actor=actor)
        target = self._get_user_or_raise(pk=target_pk)

        if actor.pk == target.pk:
            raise DjangoSelfUserManagementError()

        if target.role == "admin" and target.is_active:
            active_admin_count = User.objects.filter(
                role="admin", is_active=True
            ).count()
            if active_admin_count <= 1:
                raise DjangoLastActiveAdminError()

        target.is_active = False
        target.save(update_fields=["is_active", "updated_at"])

        self._write_audit_event(
            actor=actor,
            event_type="user_blocked",
            target=target,
        )

        return DjangoUserItem(
            pk=target.pk,
            email=target.email,
            role=target.role,
            is_active=target.is_active,
        )

    # ── activate ─────────────────────────────────────────────────────

    def activate_user(
        self,
        *,
        actor: Any,  # Django User instance
        target_pk: int,
    ) -> DjangoUserItem:
        """Transition a user to active (is_active=True)."""

        self._require_admin_actor(actor=actor)
        target = self._get_user_or_raise(pk=target_pk)

        target.is_active = True
        target.save(update_fields=["is_active", "updated_at"])

        self._write_audit_event(
            actor=actor,
            event_type="user_reactivated",
            target=target,
        )

        return DjangoUserItem(
            pk=target.pk,
            email=target.email,
            role=target.role,
            is_active=target.is_active,
        )

    # ── helpers ──────────────────────────────────────────────────────

    def _require_admin_actor(self, *, actor: Any) -> None:
        """Raise if the actor is not an active admin."""

        if not hasattr(actor, "role") or getattr(actor, "role") != "admin":
            raise DjangoUserManagementAuthorizationError()

    def _get_user_or_raise(self, *, pk: int) -> Any:
        """Return Django User or raise ``DjangoUserNotFoundError``."""

        user = User.objects.filter(pk=pk).first()
        if user is None:
            raise DjangoUserNotFoundError(f"user not found: {pk}")
        return user

    def _write_audit_event(
        self,
        *,
        actor: Any,
        event_type: str,
        target: Any,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Write an audit event synchronously to the SQLAlchemy auth_events table.

        This uses ``asyncio.run`` because it is called from
        synchronous Django view context. The ``auth_events`` table is
        the shared audit log also used by the FastAPI surface.
        """
        payload: dict[str, Any] = {
            "target_email": target.email,
            "target_role": target.role,
        }
        if extra:
            payload.update(extra)

        async def _append() -> int:
            return await self._auth_events.append_event(
                AuthEventCreateInput(
                    event_type=event_type,
                    payload=payload,
                )
            )

        asyncio.run(_append())
