"""Application role guard utilities for admin and audit access."""

from __future__ import annotations

from triage_automation.domain.auth.roles import Role, UnknownRoleError


class AuthorizationError(PermissionError):
    """Base error for explicit authorization guard failures."""


class UnknownRoleAuthorizationError(AuthorizationError):
    """Raised when a caller role value is not recognized."""


class RoleNotAuthorizedError(AuthorizationError):
    """Raised when a known role does not satisfy access requirements."""


class AccessGuardService:
    """Deterministic role checks for admin and audit-read operations."""

    def require_admin(self, *, role: Role | str) -> None:
        """Require admin role for write-capable admin operations."""

        resolved_role = self._resolve_role(role)
        if resolved_role is not Role.ADMIN:
            raise RoleNotAuthorizedError("admin role required")

    def require_audit_read(self, *, role: Role | str) -> None:
        """Require role with audit-read permission (admin or reader)."""

        resolved_role = self._resolve_role(role)
        if resolved_role not in (Role.ADMIN, Role.READER):
            raise RoleNotAuthorizedError("audit-read role required")

    def _resolve_role(self, role: Role | str) -> Role:
        try:
            return Role.from_value(role)
        except UnknownRoleError as exc:
            raise UnknownRoleAuthorizationError(str(exc)) from exc
