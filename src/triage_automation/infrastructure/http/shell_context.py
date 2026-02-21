"""Shared shell context helpers for server-rendered operational pages."""

from __future__ import annotations

from triage_automation.application.ports.user_repository_port import UserRecord
from triage_automation.domain.auth.roles import Role


def build_shell_context(
    *,
    page_title: str,
    active_nav: str,
    user: UserRecord | None,
) -> dict[str, object]:
    """Build consistent shell context for authenticated and anonymous web pages."""

    role_value = user.role.value if user is not None else None
    return {
        "page_title": page_title,
        "active_nav": active_nav,
        "shell_authenticated": user is not None,
        "shell_user_email": user.email if user is not None else "",
        "shell_user_role": role_value or "",
        "shell_can_access_prompts": user is not None and user.role is Role.ADMIN,
        "shell_can_access_users": user is not None and user.role is Role.ADMIN,
    }
