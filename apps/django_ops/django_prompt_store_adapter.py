"""Django prompt store adapter backed by the shared prompt_templates table.

Implements ``DjangoPromptStorePort`` using the existing shared
SQLAlchemy infrastructure.

**Why SQLAlchemy here (not Django ORM):**

The ``prompt_templates`` table is a genuine *shared runtime component*:
it is created and versioned by Alembic migrations and is read/written
by the LLM services, extraction pipeline, and Matrix bot — all of which
use SQLAlchemy/asyncpg.  A fully Django-native (Django ORM) persistence
path was evaluated but is blocked by the following systemic issue:

- Django's test runner manages secondary databases independently.
  Integrating an Alembic-managed schema into Django's test DB lifecycle
  requires either (a) running Alembic on Django's test DB path before
  Django opens it, or (b) preventing Django from creating a test DB
  for the alias and managing the file externally.  Both approaches
  add fragile coordination between Django's ``DiscoverRunner`` and
  Alembic's ``command.upgrade()`` that is not justified for this slice.

The SQLAlchemy session factory in ``service_wiring.py`` is already
shared across all runtime components (audit, cases, jobs, prompts).
Using it in this adapter is the *smallest clean boundary* that preserves
the approved business rules without duplicating schema management.

**What IS Django-native in this design:**

- The port (``DjangoPromptStorePort``) lives in the application layer
  and has no SQLAlchemy or Django imports.
- The application service (``DjangoPromptManagementService``) enforces
  business rules and audit semantics with no infrastructure imports.
- The adapter is thin: it only translates between the port contracts
  and the shared SQLAlchemy repository.
- Audit events use the Django actor-identity pattern (``user_id=NULL``,
  actor info in payload) established by ``DjangoUserManagementService``.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from triage_automation.application.ports.django_prompt_store_port import (
    DjangoPromptStorePort,
)
from triage_automation.application.ports.prompt_management_repository_port import (
    PromptManagementRepositoryPort,
    PromptVersionContentRecord,
    PromptVersionRecord,
)


class DjangoOrmPromptStoreAdapter(DjangoPromptStorePort):
    """SQLAlchemy-backed adapter implementing ``DjangoPromptStorePort``.

    Wraps the shared ``PromptManagementRepositoryPort`` for reads
    and performs mutations directly via SQLAlchemy sessions so that
    ``updated_by_user_id`` remains NULL (Django users have integer
    PKs, not UUIDs).  See module docstring for the rationale behind
    keeping SQLAlchemy in this adapter.
    """

    def __init__(
        self,
        *,
        prompt_management: PromptManagementRepositoryPort,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._prompt_management = prompt_management
        self._session_factory = session_factory

    # ── Reads (delegate to shared port) ──────────────────────────

    async def list_versions(self) -> list[PromptVersionRecord]:
        """Return all prompt versions via the shared read port."""
        return await self._prompt_management.list_prompt_versions()

    async def get_version(
        self, *, name: str, version: int
    ) -> PromptVersionContentRecord | None:
        """Return one prompt version via the shared read port."""
        return await self._prompt_management.get_prompt_version(
            name=name, version=version
        )

    # ── Mutations (direct session, updated_by_user_id=NULL) ──────

    async def activate_version(
        self, *, name: str, version: int
    ) -> PromptVersionRecord | None:
        """Atomically activate one prompt version, deactivating others.

        Uses a SQLAlchemy transaction directly so that
        ``updated_by_user_id`` is set to NULL (no UUID FK).
        """
        from datetime import UTC, datetime

        import sqlalchemy as sa

        from triage_automation.infrastructure.db.metadata import prompt_templates

        now = datetime.now(tz=UTC)

        async with self._session_factory() as session:
            async with session.begin():
                target_result = await session.execute(
                    sa.select(
                        prompt_templates.c.name,
                        prompt_templates.c.version,
                        prompt_templates.c.is_active,
                    )
                    .where(
                        prompt_templates.c.name == name,
                        prompt_templates.c.version == version,
                    )
                    .limit(1)
                )
                if target_result.mappings().first() is None:
                    return None

                await session.execute(
                    sa.update(prompt_templates)
                    .where(
                        prompt_templates.c.name == name,
                        prompt_templates.c.is_active.is_(True),
                    )
                    .values(is_active=False, updated_at=now)
                )

                await session.execute(
                    sa.update(prompt_templates)
                    .where(
                        prompt_templates.c.name == name,
                        prompt_templates.c.version == version,
                    )
                    .values(is_active=True, updated_at=now)
                )

            refreshed = await session.execute(
                sa.select(
                    prompt_templates.c.name,
                    prompt_templates.c.version,
                    prompt_templates.c.is_active,
                )
                .where(
                    prompt_templates.c.name == name,
                    prompt_templates.c.version == version,
                )
                .limit(1)
            )

        row = refreshed.mappings().first()
        if row is None:
            return None
        return PromptVersionRecord(
            name=str(row["name"]),
            version=int(row["version"]),
            is_active=bool(row["is_active"]),
        )

    async def create_version(
        self,
        *,
        name: str,
        source_version: int,
        content: str,
    ) -> PromptVersionRecord | None:
        """Insert a new inactive version derived from source_version.

        Uses a SQLAlchemy transaction directly so that
        ``updated_by_user_id`` is set to NULL.
        """
        from datetime import UTC, datetime

        import sqlalchemy as sa

        from triage_automation.infrastructure.db.metadata import prompt_templates

        now = datetime.now(tz=UTC)

        async with self._session_factory() as session:
            async with session.begin():
                source_result = await session.execute(
                    sa.select(prompt_templates.c.version)
                    .where(
                        prompt_templates.c.name == name,
                        prompt_templates.c.version == source_version,
                    )
                    .limit(1)
                )
                if source_result.mappings().first() is None:
                    return None

                next_version_stmt = sa.select(
                    sa.func.coalesce(
                        sa.func.max(prompt_templates.c.version), 0
                    )
                    + 1
                ).where(prompt_templates.c.name == name)
                next_version = await session.scalar(next_version_stmt)
                assert next_version is not None

                await session.execute(
                    sa.insert(prompt_templates).values(
                        id=uuid4(),
                        name=name,
                        version=int(next_version),
                        content=content,
                        is_active=False,
                        created_at=now,
                        updated_at=now,
                    )
                )

            refreshed = await session.execute(
                sa.select(
                    prompt_templates.c.name,
                    prompt_templates.c.version,
                    prompt_templates.c.is_active,
                )
                .where(
                    prompt_templates.c.name == name,
                    prompt_templates.c.version == int(next_version),
                )
                .limit(1)
            )

        row = refreshed.mappings().first()
        if row is None:
            return None
        return PromptVersionRecord(
            name=str(row["name"]),
            version=int(row["version"]),
            is_active=bool(row["is_active"]),
        )
