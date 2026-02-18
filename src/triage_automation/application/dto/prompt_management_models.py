"""Pydantic models for admin prompt-management API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Base model with strict unknown-field rejection."""

    model_config = ConfigDict(extra="forbid")


class PromptVersionItem(StrictModel):
    """Prompt version metadata for catalog and active-state responses."""

    name: str
    version: int = Field(ge=1)
    is_active: bool


class PromptVersionListResponse(StrictModel):
    """Response model for prompt-version catalog listing."""

    items: list[PromptVersionItem]


class PromptActivationRequest(StrictModel):
    """Request payload for selecting a prompt version to activate."""

    version: int = Field(ge=1)
