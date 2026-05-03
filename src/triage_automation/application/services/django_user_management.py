"""Application service for Django-backed user management.

Depends only on application-layer ports (``DjangoUserStorePort``,
``AuthEventRepositoryPort``) — never imports Django ORM directly.

Uses the same audit payload structure as ``UserManagementService``
so both surfaces produce equivalent administrative audit evidence.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from triage_automation.application.ports.auth_event_repository_port import (
    AuthEventCreateInput,
    AuthEventRepositoryPort,
)
from triage_automation.application.ports.django_user_store_port import (
    DjangoCreateUserRequest,
    DjangoUserItem,
    DjangoUserStorePort,
)

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


# ── Actor DTO (carried through views → service) ──────────────────────


@dataclass(frozen=True)
class DjangoActor:
    """Minimal actor representation passed from Django views."""

    pk: int
    email: str
    role: str


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


def _status_from_active(is_active: bool) -> str:
    """Translate is_active boolean to a human-readable status label."""
    return "active" if is_active else "blocked"


# ── Service ──────────────────────────────────────────────────────────


class DjangoUserManagementService:
    """User management for the consolidated Django admin surface.

    Depends on ``DjangoUserStorePort`` for persistence and
    ``AuthEventRepositoryPort`` for audit — no Django ORM imports.
    """

    def __init__(
        self,
        *,
        store: DjangoUserStorePort,
        auth_events: AuthEventRepositoryPort,
    ) -> None:
        self._store = store
        self._auth_events = auth_events

    # ── list ─────────────────────────────────────────────────────────

    def list_users(self) -> list[DjangoUserItem]:
        """Return deterministic user listing for admin pages."""

        return self._store.list_users()

    # ── create ───────────────────────────────────────────────────────

    def create_user(
        self,
        *,
        actor: DjangoActor,
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

        if self._store.email_exists(email=email):
            raise DjangoEmailAlreadyExistsError()

        created = self._store.create_user(
            email=email,
            password=password,
            role=role_value,
        )

        self._write_audit_event(
            actor=actor,
            event_type="user_created",
            target=created,
            previous_status=None,
            new_status="active",
        )

        return created

    # ── update_role ──────────────────────────────────────────────────

    def update_user_role(
        self,
        *,
        actor: DjangoActor,
        target_pk: int,
        new_role: str,
    ) -> DjangoUserItem:
        """Change the role of an existing user."""

        self._require_admin_actor(actor=actor)
        role_value = _to_operational_role(new_role)

        target = self._get_user_or_raise(pk=target_pk)

        # Preserve last-active-admin invariant.
        if target.role == "admin" and role_value != "admin":
            if self._store.count_active_by_role(role="admin") <= 1:
                raise DjangoLastActiveAdminError()

        old_role = target.role
        updated = self._store.update_role(pk=target_pk, role=role_value)

        self._write_audit_event(
            actor=actor,
            event_type="user_role_changed",
            target=updated,
            previous_status=None,
            new_status=None,
            extra={"old_role": old_role, "new_role": role_value},
        )

        return updated

    # ── block ────────────────────────────────────────────────────────

    def block_user(
        self,
        *,
        actor: DjangoActor,
        target_pk: int,
    ) -> DjangoUserItem:
        """Transition a user to blocked (is_active=False)."""

        self._require_admin_actor(actor=actor)
        target = self._get_user_or_raise(pk=target_pk)

        if actor.pk == target.pk:
            raise DjangoSelfUserManagementError()

        if target.role == "admin" and target.is_active:
            if self._store.count_active_by_role(role="admin") <= 1:
                raise DjangoLastActiveAdminError()

        previous_status = _status_from_active(target.is_active)
        updated = self._store.set_active(pk=target_pk, is_active=False)
        new_status = _status_from_active(updated.is_active)

        self._write_audit_event(
            actor=actor,
            event_type="user_blocked",
            target=updated,
            previous_status=previous_status,
            new_status=new_status,
        )

        return updated

    # ── activate ─────────────────────────────────────────────────────

    def activate_user(
        self,
        *,
        actor: DjangoActor,
        target_pk: int,
    ) -> DjangoUserItem:
        """Transition a user to active (is_active=True)."""

        self._require_admin_actor(actor=actor)
        target = self._get_user_or_raise(pk=target_pk)

        previous_status = _status_from_active(target.is_active)
        updated = self._store.set_active(pk=target_pk, is_active=True)
        new_status = _status_from_active(updated.is_active)

        self._write_audit_event(
            actor=actor,
            event_type="user_reactivated",
            target=updated,
            previous_status=previous_status,
            new_status=new_status,
        )

        return updated

    # ── helpers ──────────────────────────────────────────────────────

    def _require_admin_actor(self, *, actor: DjangoActor) -> None:
        """Raise if the actor is not an admin."""

        if actor.role != "admin":
            raise DjangoUserManagementAuthorizationError()

    def _get_user_or_raise(self, *, pk: int) -> DjangoUserItem:
        """Return user or raise ``DjangoUserNotFoundError``."""

        user = self._store.get_by_pk(pk=pk)
        if user is None:
            raise DjangoUserNotFoundError(f"user not found: {pk}")
        return user

    def _write_audit_event(
        self,
        *,
        actor: DjangoActor,
        event_type: str,
        target: DjangoUserItem,
        previous_status: str | None,
        new_status: str | None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Write an audit event for a Django admin management action.

        Sets ``auth_events.user_id`` to ``None`` because Django actors
        have no authoritative UUID in the SQLAlchemy ``users`` table.
        All actor/target identity is carried in the ``payload`` field
        (``actor_user_id`` as Django PK string and ``actor_email``),
        keeping the audit trail complete without fabricating UUIDs.
        """
        payload: dict[str, Any] = {
            "target_user_id": str(target.pk),
            "target_email": target.email,
            "target_role": target.role,
            "actor_user_id": str(actor.pk),
            "actor_email": actor.email,
            "previous_status": previous_status,
            "new_status": new_status,
        }
        if extra:
            payload.update(extra)

        async def _append() -> int:
            return await self._auth_events.append_event(
                AuthEventCreateInput(
                    event_type=event_type,
                    user_id=None,
                    payload=payload,
                )
            )

        asyncio.run(_append())
