from __future__ import annotations

import pytest

from triage_automation.application.services.access_guard_service import (
    AccessGuardService,
    RoleNotAuthorizedError,
    UnknownRoleAuthorizationError,
)
from triage_automation.domain.auth.roles import Role


def test_admin_satisfies_admin_required_guard() -> None:
    guard = AccessGuardService()

    guard.require_admin(role=Role.ADMIN)


def test_reader_denied_for_admin_required_guard() -> None:
    guard = AccessGuardService()

    with pytest.raises(RoleNotAuthorizedError, match="admin role required"):
        guard.require_admin(role=Role.READER)


def test_reader_allowed_for_audit_read_guard() -> None:
    guard = AccessGuardService()

    guard.require_audit_read(role=Role.READER)


def test_unknown_role_rejected_explicitly() -> None:
    guard = AccessGuardService()

    with pytest.raises(UnknownRoleAuthorizationError, match="Unknown role: owner"):
        guard.require_audit_read(role="owner")
