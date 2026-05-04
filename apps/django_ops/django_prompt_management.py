"""Django-compatible prompt management service for the consolidated admin surface.

Uses the shared ``PromptManagementRepositoryPort`` for reads and
writes directly via SQLAlchemy for mutations (bypassing the UUID
``updated_by_user_id`` FK constraint), and ``AuthEventRepositoryPort``
for audit with the Django actor-identity pattern (user_id=NULL,
actor info in payload).
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from triage_automation.application.ports.auth_event_repository_port import (
    AuthEventCreateInput,
    AuthEventRepositoryPort,
)
from triage_automation.application.ports.prompt_management_repository_port import (
    PromptManagementRepositoryPort,
    PromptVersionContentRecord,
    PromptVersionRecord,
)


class DjangoPromptManagementError(Exception):
    """Base error for Django prompt management operations."""


class DjangoPromptVersionNotFoundError(DjangoPromptManagementError):
    """Raised when a referenced prompt version does not exist."""


class DjangoPromptManagementService:
    """Prompt management for the consolidated Django admin surface.

    Depends on ``PromptManagementRepositoryPort`` for reads and
    ``AuthEventRepositoryPort`` for audit.  Mutation methods use
    direct SQLAlchemy session access so that ``updated_by_user_id``
    remains NULL (no UUID FK matching Django integer primary keys).
    """

    def __init__(
        self,
        *,
        prompt_management: PromptManagementRepositoryPort,
        auth_events: AuthEventRepositoryPort,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._prompt_management = prompt_management
        self._auth_events = auth_events
        self._session_factory = session_factory

    # ── Reads (delegate to shared port) ──────────────────────────

    async def list_versions(self) -> list[PromptVersionRecord]:
        """Return all available prompt versions with active-state markers."""
        return await self._prompt_management.list_prompt_versions()

    async def get_active_version(
        self, *, prompt_name: str
    ) -> PromptVersionRecord | None:
        """Return active prompt version for name, if one is currently active."""
        return await self._prompt_management.get_active_prompt_version(
            name=prompt_name
        )

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

    # ── Mutations (write with updated_by_user_id=NULL) ───────────

    async def activate_version(
        self,
        *,
        prompt_name: str,
        version: int,
        actor_pk: int,
        actor_email: str,
    ) -> PromptVersionRecord:
        """Activate one prompt version and return the resulting active record.

        Writes ``updated_by_user_id=NULL`` and appends an audit event
        with Django actor identity in the payload.
        """
        from datetime import UTC, datetime

        import sqlalchemy as sa

        from triage_automation.infrastructure.db.metadata import prompt_templates

        now = datetime.now(tz=UTC)

        async with self._session_factory() as session:
            async with session.begin():
                # Verify target exists.
                target_result = await session.execute(
                    sa.select(
                        prompt_templates.c.name,
                        prompt_templates.c.version,
                        prompt_templates.c.is_active,
                    )
                    .where(
                        prompt_templates.c.name == prompt_name,
                        prompt_templates.c.version == version,
                    )
                    .limit(1)
                )
                target_row = target_result.mappings().first()
                if target_row is None:
                    raise DjangoPromptVersionNotFoundError(
                        f"prompt version not found: {prompt_name}@{version}"
                    )

                # Deactivate any currently active version for this name.
                await session.execute(
                    sa.update(prompt_templates)
                    .where(
                        prompt_templates.c.name == prompt_name,
                        prompt_templates.c.is_active.is_(True),
                    )
                    .values(is_active=False, updated_at=now)
                )

                # Activate the selected version.
                await session.execute(
                    sa.update(prompt_templates)
                    .where(
                        prompt_templates.c.name == prompt_name,
                        prompt_templates.c.version == version,
                    )
                    .values(is_active=True, updated_at=now)
                )

            # Re-read to return the activated record.
            refreshed = await session.execute(
                sa.select(
                    prompt_templates.c.name,
                    prompt_templates.c.version,
                    prompt_templates.c.is_active,
                )
                .where(
                    prompt_templates.c.name == prompt_name,
                    prompt_templates.c.version == version,
                )
                .limit(1)
            )

        row = refreshed.mappings().first()
        if row is None:
            raise DjangoPromptVersionNotFoundError(
                f"prompt version disappeared: {prompt_name}@{version}"
            )

        activated = PromptVersionRecord(
            name=str(row["name"]),
            version=int(row["version"]),
            is_active=bool(row["is_active"]),
        )

        # ── Audit ────────────────────────────────────────────────
        await self._auth_events.append_event(
            AuthEventCreateInput(
                user_id=None,
                event_type="prompt_version_activated",
                payload={
                    "action": "activate_prompt_version",
                    "prompt_name": prompt_name,
                    "version": version,
                    "actor_user_id": str(actor_pk),
                    "actor_email": actor_email,
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
        actor_pk: int,
        actor_email: str,
    ) -> PromptVersionRecord:
        """Create next prompt version derived from source version content baseline.

        Writes ``updated_by_user_id=NULL`` and appends an audit event
        with Django actor identity in the payload.
        """
        from datetime import UTC, datetime

        import sqlalchemy as sa

        from triage_automation.infrastructure.db.metadata import prompt_templates

        now = datetime.now(tz=UTC)

        async with self._session_factory() as session:
            async with session.begin():
                # Verify source version exists.
                source_result = await session.execute(
                    sa.select(prompt_templates.c.version)
                    .where(
                        prompt_templates.c.name == prompt_name,
                        prompt_templates.c.version == source_version,
                    )
                    .limit(1)
                )
                if source_result.mappings().first() is None:
                    raise DjangoPromptVersionNotFoundError(
                        f"source prompt version not found: {prompt_name}@{source_version}"
                    )

                # Compute next version number.
                next_version_stmt = sa.select(
                    sa.func.coalesce(
                        sa.func.max(prompt_templates.c.version), 0
                    )
                    + 1
                ).where(prompt_templates.c.name == prompt_name)
                next_version = await session.scalar(next_version_stmt)
                assert next_version is not None

                # Insert new inactive version.
                await session.execute(
                    sa.insert(prompt_templates).values(
                        id=uuid4(),
                        name=prompt_name,
                        version=int(next_version),
                        content=content,
                        is_active=False,
                        created_at=now,
                        updated_at=now,
                    )
                )

            # Re-read to return the created record.
            refreshed = await session.execute(
                sa.select(
                    prompt_templates.c.name,
                    prompt_templates.c.version,
                    prompt_templates.c.is_active,
                )
                .where(
                    prompt_templates.c.name == prompt_name,
                    prompt_templates.c.version == int(next_version),
                )
                .limit(1)
            )

        row = refreshed.mappings().first()
        if row is None:
            raise DjangoPromptVersionNotFoundError(
                f"created prompt version disappeared: {prompt_name}@{next_version}"
            )

        created = PromptVersionRecord(
            name=str(row["name"]),
            version=int(row["version"]),
            is_active=bool(row["is_active"]),
        )

        # ── Audit ────────────────────────────────────────────────
        await self._auth_events.append_event(
            AuthEventCreateInput(
                user_id=None,
                event_type="prompt_version_created",
                payload={
                    "action": "create_prompt_version",
                    "prompt_name": prompt_name,
                    "source_version": source_version,
                    "version": int(next_version),
                    "actor_user_id": str(actor_pk),
                    "actor_email": actor_email,
                },
            )
        )
        return created
