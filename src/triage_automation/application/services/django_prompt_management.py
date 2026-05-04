"""Application service for Django-admin prompt management.

Contains the business logic for prompt-version activation (CAS
semantics), version creation (derived from source), and audit-event
persistence for the consolidated Django admin surface.

Delegates all storage operations to ``DjangoPromptStorePort`` and
all audit writes to ``AuthEventRepositoryPort`` — never imports
SQLAlchemy, Django ORM, or framework-specific infrastructure.
"""

from __future__ import annotations

from triage_automation.application.ports.auth_event_repository_port import (
    AuthEventCreateInput,
    AuthEventRepositoryPort,
)
from triage_automation.application.ports.django_prompt_store_port import (
    DjangoPromptStorePort,
)
from triage_automation.application.ports.prompt_management_repository_port import (
    PromptVersionContentRecord,
    PromptVersionRecord,
)

# ── Domain errors ──────────────────────────────────────────────────


class DjangoPromptManagementError(Exception):
    """Base error for Django prompt management operations."""


class DjangoPromptVersionNotFoundError(DjangoPromptManagementError):
    """Raised when a referenced prompt version does not exist."""


# ── Actor DTO (carried through views → service) ────────────────────


class DjangoPromptActor:
    """Minimal actor representation passed from Django views.

    Uses plain string identity (no PK type coupling) so the service
    works with both integer and UUID primary keys.
    """

    def __init__(self, *, pk: object, email: str) -> None:
        self._pk = pk
        self.email = email

    @property
    def pk_str(self) -> str:
        """Return the primary key as a string for audit payloads."""
        return str(self._pk)


# ── Service ────────────────────────────────────────────────────────


class DjangoPromptManagementService:
    """Prompt management for the consolidated Django admin surface.

    Depends on ``DjangoPromptStorePort`` for persistence and
    ``AuthEventRepositoryPort`` for audit.  All business rules
    (at-most-one-active, version derivation, audit) are enforced
    here without any framework or infrastructure imports.
    """

    def __init__(
        self,
        *,
        store: DjangoPromptStorePort,
        auth_events: AuthEventRepositoryPort,
    ) -> None:
        self._store = store
        self._auth_events = auth_events

    # ── Reads ──────────────────────────────────────────────────────

    async def list_versions(self) -> list[PromptVersionRecord]:
        """Return all available prompt versions with active-state markers."""
        return await self._store.list_versions()

    async def get_version(
        self,
        *,
        prompt_name: str,
        version: int,
    ) -> PromptVersionContentRecord | None:
        """Return one prompt version including immutable content body."""
        return await self._store.get_version(name=prompt_name, version=version)

    # ── Mutations ──────────────────────────────────────────────────

    async def activate_version(
        self,
        *,
        prompt_name: str,
        version: int,
        actor: DjangoPromptActor,
    ) -> PromptVersionRecord:
        """Activate one prompt version and return the resulting active record.

        The store performs an atomic activation (deactivate current,
        activate selected).  On success, an audit event is appended
        with Django actor identity in the payload.
        """

        activated = await self._store.activate_version(
            name=prompt_name,
            version=version,
        )
        if activated is None:
            raise DjangoPromptVersionNotFoundError(
                f"prompt version not found: {prompt_name}@{version}"
            )

        await self._auth_events.append_event(
            AuthEventCreateInput(
                user_id=None,
                event_type="prompt_version_activated",
                payload={
                    "action": "activate_prompt_version",
                    "prompt_name": prompt_name,
                    "version": version,
                    "actor_user_id": actor.pk_str,
                    "actor_email": actor.email,
                },
            )
        )
        return activated

    async def create_version(
        self,
        *,
        prompt_name: str,
        source_version: int,
        content: str,
        actor: DjangoPromptActor,
    ) -> PromptVersionRecord:
        """Create next prompt version derived from an existing source version.

        The store computes the next version number and inserts an
        inactive record.  On success, an audit event is appended.
        """

        created = await self._store.create_version(
            name=prompt_name,
            source_version=source_version,
            content=content,
        )
        if created is None:
            raise DjangoPromptVersionNotFoundError(
                f"source prompt version not found: {prompt_name}@{source_version}"
            )

        await self._auth_events.append_event(
            AuthEventCreateInput(
                user_id=None,
                event_type="prompt_version_created",
                payload={
                    "action": "create_prompt_version",
                    "prompt_name": prompt_name,
                    "source_version": source_version,
                    "version": created.version,
                    "actor_user_id": actor.pk_str,
                    "actor_email": actor.email,
                },
            )
        )
        return created
