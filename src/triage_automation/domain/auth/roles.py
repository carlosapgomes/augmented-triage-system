"""Role enum definitions for admin and reader access control."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    """Supported user roles."""

    ADMIN = "admin"
    READER = "reader"
