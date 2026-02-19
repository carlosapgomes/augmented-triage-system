"""SQLAlchemy adapter for prompt template retrieval queries."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from triage_automation.application.ports.prompt_management_repository_port import (
    PromptManagementRepositoryPort,
    PromptVersionContentRecord,
    PromptVersionRecord,
)
from triage_automation.application.ports.prompt_template_repository_port import (
    PromptTemplateRecord,
    PromptTemplateRepositoryPort,
)
from triage_automation.infrastructure.db.metadata import prompt_templates


class SqlAlchemyPromptTemplateRepository(
    PromptTemplateRepositoryPort, PromptManagementRepositoryPort
):
    """Prompt template repository backed by SQLAlchemy async sessions."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_active_by_name(self, *, name: str) -> PromptTemplateRecord | None:
        """Return latest active template version for the provided prompt name."""

        statement = (
            sa.select(
                prompt_templates.c.name,
                prompt_templates.c.version,
                prompt_templates.c.content,
            )
            .where(
                prompt_templates.c.name == name,
                prompt_templates.c.is_active.is_(True),
            )
            .order_by(prompt_templates.c.version.desc())
            .limit(1)
        )

        async with self._session_factory() as session:
            result = await session.execute(statement)

        row = result.mappings().first()
        if row is None:
            return None

        return PromptTemplateRecord(
            name=cast(str, row["name"]),
            version=int(row["version"]),
            content=cast(str, row["content"]),
        )

    async def list_prompt_versions(self) -> list[PromptVersionRecord]:
        """Return all prompt versions ordered by prompt name and newest version first."""

        statement = sa.select(
            prompt_templates.c.name,
            prompt_templates.c.version,
            prompt_templates.c.is_active,
        ).order_by(prompt_templates.c.name.asc(), prompt_templates.c.version.desc())

        async with self._session_factory() as session:
            result = await session.execute(statement)

        return [_to_prompt_version_record(row) for row in result.mappings().all()]

    async def get_active_prompt_version(self, *, name: str) -> PromptVersionRecord | None:
        """Return active version metadata for prompt name, or None when absent."""

        statement = (
            sa.select(
                prompt_templates.c.name,
                prompt_templates.c.version,
                prompt_templates.c.is_active,
            )
            .where(
                prompt_templates.c.name == name,
                prompt_templates.c.is_active.is_(True),
            )
            .order_by(prompt_templates.c.version.desc())
            .limit(1)
        )

        async with self._session_factory() as session:
            result = await session.execute(statement)

        row = result.mappings().first()
        if row is None:
            return None
        return _to_prompt_version_record(row)

    async def activate_prompt_version(
        self,
        *,
        name: str,
        version: int,
        updated_by_user_id: UUID,
    ) -> PromptVersionRecord | None:
        """Activate one prompt version while preserving a single active row per prompt name."""

        select_target = (
            sa.select(
                prompt_templates.c.name,
                prompt_templates.c.version,
                prompt_templates.c.is_active,
            )
            .where(prompt_templates.c.name == name, prompt_templates.c.version == version)
            .limit(1)
        )
        now = datetime.now(tz=UTC)

        async with self._session_factory() as session:
            async with session.begin():
                target_result = await session.execute(select_target)
                target_row = target_result.mappings().first()
                if target_row is None:
                    return None

                await session.execute(
                    sa.update(prompt_templates)
                    .where(prompt_templates.c.name == name, prompt_templates.c.is_active.is_(True))
                    .values(is_active=False, updated_at=now, updated_by_user_id=updated_by_user_id)
                )
                await session.execute(
                    sa.update(prompt_templates)
                    .where(prompt_templates.c.name == name, prompt_templates.c.version == version)
                    .values(is_active=True, updated_at=now, updated_by_user_id=updated_by_user_id)
                )

            refreshed = await session.execute(
                sa.select(
                    prompt_templates.c.name,
                    prompt_templates.c.version,
                    prompt_templates.c.is_active,
                )
                .where(prompt_templates.c.name == name, prompt_templates.c.version == version)
                .limit(1)
            )

        row = refreshed.mappings().first()
        if row is None:
            return None
        return _to_prompt_version_record(row)

    async def get_prompt_version(
        self,
        *,
        name: str,
        version: int,
    ) -> PromptVersionContentRecord | None:
        """Return one prompt version with immutable text body and active-state marker."""

        statement = (
            sa.select(
                prompt_templates.c.name,
                prompt_templates.c.version,
                prompt_templates.c.is_active,
                prompt_templates.c.content,
            )
            .where(
                prompt_templates.c.name == name,
                prompt_templates.c.version == version,
            )
            .limit(1)
        )
        async with self._session_factory() as session:
            result = await session.execute(statement)

        row = result.mappings().first()
        if row is None:
            return None
        return _to_prompt_version_content_record(row)

    async def create_prompt_version(
        self,
        *,
        name: str,
        source_version: int,
        content: str,
        updated_by_user_id: UUID,
    ) -> PromptVersionRecord | None:
        """Insert a new inactive prompt version derived from an existing source version."""

        now = datetime.now(tz=UTC)
        select_source = (
            sa.select(prompt_templates.c.version)
            .where(
                prompt_templates.c.name == name,
                prompt_templates.c.version == source_version,
            )
            .limit(1)
        )

        async with self._session_factory() as session:
            async with session.begin():
                source_row = (await session.execute(select_source)).mappings().first()
                if source_row is None:
                    return None

                next_version_statement = sa.select(
                    sa.func.coalesce(sa.func.max(prompt_templates.c.version), 0) + 1
                ).where(prompt_templates.c.name == name)
                next_version = await session.scalar(
                    next_version_statement
                )
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
                        updated_by_user_id=updated_by_user_id,
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
        return _to_prompt_version_record(row)


def _to_prompt_version_record(row: sa.RowMapping) -> PromptVersionRecord:
    """Convert SQLAlchemy row mapping into prompt version metadata record."""

    return PromptVersionRecord(
        name=cast(str, row["name"]),
        version=int(row["version"]),
        is_active=bool(row["is_active"]),
    )


def _to_prompt_version_content_record(row: sa.RowMapping) -> PromptVersionContentRecord:
    """Convert SQLAlchemy row mapping into prompt version record with content."""

    return PromptVersionContentRecord(
        name=cast(str, row["name"]),
        version=int(row["version"]),
        is_active=bool(row["is_active"]),
        content=cast(str, row["content"]),
    )
