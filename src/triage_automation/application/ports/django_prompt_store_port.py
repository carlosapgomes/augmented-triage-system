"""Port for Django-native prompt-template persistence operations.

Defines the data contract between the application-layer
``DjangoPromptManagementService`` and the adapter in the
infrastructure / Django adapter layer.

Reuses ``PromptVersionRecord`` and ``PromptVersionContentRecord``
from the shared ``prompt_management_repository_port`` so that
the Django consolidated surface and the legacy surface produce
identical read models.
"""

from __future__ import annotations

from typing import Protocol

from triage_automation.application.ports.prompt_management_repository_port import (
    PromptVersionContentRecord,
    PromptVersionRecord,
)


class DjangoPromptStorePort(Protocol):
    """Repository contract for Django-native prompt-template operations.

    Implementations bridge between the application-layer service and
    the actual storage (shared prompt_templates table). The adapter
    is responsible for hiding storage concerns such as the
    ``updated_by_user_id`` column or UUID vs integer primary keys.
    """

    async def list_versions(self) -> list[PromptVersionRecord]:
        """Return all prompt versions with active-state markers."""

    async def get_version(
        self, *, name: str, version: int
    ) -> PromptVersionContentRecord | None:
        """Return one prompt version with immutable content, or None."""

    async def activate_version(
        self, *, name: str, version: int
    ) -> PromptVersionRecord | None:
        """Atomically activate one prompt version and return it, or None.

        The implementation MUST deactivate any currently-active version
        for the same prompt name in the same unit-of-work so that at
        most one version per name is active at any time.
        """

    async def create_version(
        self,
        *,
        name: str,
        source_version: int,
        content: str,
    ) -> PromptVersionRecord | None:
        """Create a new inactive version derived from an existing source.

        Returns the newly created record, or None if ``source_version``
        does not exist.  The implementation MUST compute the next
        version number deterministically (MAX + 1).
        """
