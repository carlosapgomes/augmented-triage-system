"""Port contracts for prompt-management read and activation operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class PromptVersionRecord:
    """Prompt version metadata used by admin prompt-management flows."""

    name: str
    version: int
    is_active: bool


@dataclass(frozen=True)
class PromptVersionContentRecord:
    """Prompt version metadata plus immutable content payload."""

    name: str
    version: int
    is_active: bool
    content: str


class PromptManagementRepositoryPort(Protocol):
    """Prompt-management repository contract used by admin services."""

    async def list_prompt_versions(self) -> list[PromptVersionRecord]:
        """Return all persisted prompt versions with active-state flags."""

    async def get_active_prompt_version(self, *, name: str) -> PromptVersionRecord | None:
        """Return active prompt version metadata for name, or None when absent."""

    async def activate_prompt_version(
        self,
        *,
        name: str,
        version: int,
        updated_by_user_id: UUID,
    ) -> PromptVersionRecord | None:
        """Set selected prompt version active and return it, or None when missing."""

    async def get_prompt_version(
        self,
        *,
        name: str,
        version: int,
    ) -> PromptVersionContentRecord | None:
        """Return one prompt version with immutable content, or None when missing."""

    async def create_prompt_version(
        self,
        *,
        name: str,
        source_version: int,
        content: str,
        updated_by_user_id: UUID,
    ) -> PromptVersionRecord | None:
        """Create next derived version, or return None when source version is missing."""
