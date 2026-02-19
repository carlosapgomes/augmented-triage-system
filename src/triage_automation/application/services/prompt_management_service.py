"""Application service for admin prompt-management operations."""

from __future__ import annotations

from uuid import UUID

from triage_automation.application.ports.auth_event_repository_port import (
    AuthEventCreateInput,
    AuthEventRepositoryPort,
)
from triage_automation.application.ports.prompt_management_repository_port import (
    PromptManagementRepositoryPort,
    PromptVersionContentRecord,
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

    def __init__(
        self,
        *,
        prompt_management: PromptManagementRepositoryPort,
        auth_events: AuthEventRepositoryPort,
    ) -> None:
        self._prompt_management = prompt_management
        self._auth_events = auth_events

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

        await self._auth_events.append_event(
            AuthEventCreateInput(
                user_id=actor_user_id,
                event_type="prompt_version_activated",
                payload={
                    "action": "activate_prompt_version",
                    "prompt_name": prompt_name,
                    "version": version,
                },
            )
        )
        return activated

    async def get_version(
        self,
        *,
        prompt_name: str,
        version: int,
    ) -> PromptVersionContentRecord | None:
        """Return one prompt version including immutable content body."""

        return await self._prompt_management.get_prompt_version(
            name=prompt_name,
            version=version,
        )

    async def create_version(
        self,
        *,
        prompt_name: str,
        source_version: int,
        content: str,
        actor_user_id: UUID,
    ) -> PromptVersionRecord:
        """Create next prompt version derived from source version content baseline."""

        created = await self._prompt_management.create_prompt_version(
            name=prompt_name,
            source_version=source_version,
            content=content,
            updated_by_user_id=actor_user_id,
        )
        if created is None:
            raise PromptVersionNotFoundError(name=prompt_name, version=source_version)

        await self._auth_events.append_event(
            AuthEventCreateInput(
                user_id=actor_user_id,
                event_type="prompt_version_created",
                payload={
                    "action": "create_prompt_version",
                    "prompt_name": prompt_name,
                    "source_version": source_version,
                    "version": created.version,
                },
            )
        )
        return created
