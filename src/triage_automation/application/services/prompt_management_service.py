"""Application service for admin prompt-management operations."""

from __future__ import annotations

from uuid import UUID

from triage_automation.application.ports.prompt_management_repository_port import (
    PromptManagementRepositoryPort,
    PromptVersionRecord,
)


class PromptVersionNotFoundError(LookupError):
    """Raised when a referenced prompt version does not exist."""

    def __init__(self, *, name: str, version: int) -> None:
        super().__init__(f"prompt version not found: {name}@{version}")
        self.name = name
        self.version = version


class PromptManagementService:
    """Expose prompt version catalog and activation use-cases."""

    def __init__(self, *, prompt_management: PromptManagementRepositoryPort) -> None:
        self._prompt_management = prompt_management

    async def list_versions(self) -> list[PromptVersionRecord]:
        """Return all available prompt versions with active-state markers."""

        return await self._prompt_management.list_prompt_versions()

    async def get_active_version(self, *, prompt_name: str) -> PromptVersionRecord | None:
        """Return active prompt version for name, if one is currently active."""

        return await self._prompt_management.get_active_prompt_version(name=prompt_name)

    async def activate_version(
        self,
        *,
        prompt_name: str,
        version: int,
        actor_user_id: UUID,
    ) -> PromptVersionRecord:
        """Activate one prompt version and return resulting active record."""

        activated = await self._prompt_management.activate_prompt_version(
            name=prompt_name,
            version=version,
            updated_by_user_id=actor_user_id,
        )
        if activated is None:
            raise PromptVersionNotFoundError(name=prompt_name, version=version)
        return activated
