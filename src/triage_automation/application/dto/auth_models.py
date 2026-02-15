"""Pydantic models for login request/response contracts."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from triage_automation.domain.auth.roles import Role


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginRequest(StrictModel):
    """HTTP request body contract for opaque-token login."""

    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


class LoginResponse(StrictModel):
    """HTTP success response for opaque-token login."""

    token: str = Field(min_length=1)
    role: Role
    expires_at: datetime
