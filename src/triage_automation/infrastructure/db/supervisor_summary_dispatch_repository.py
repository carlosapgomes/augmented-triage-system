"""SQLAlchemy adapter for Room-4 supervisor summary dispatch persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

import sqlalchemy as sa
from sqlalchemy.engine import CursorResult, RowMapping
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from triage_automation.application.ports.supervisor_summary_dispatch_repository_port import (
    SupervisorSummaryDispatchRecord,
    SupervisorSummaryDispatchRepositoryPort,
    SupervisorSummaryDispatchSentInput,
    SupervisorSummaryDispatchStatus,
    SupervisorSummaryWindowKey,
)
from triage_automation.infrastructure.db.metadata import supervisor_summary_dispatches


def _is_duplicate_room_window_error(error: IntegrityError) -> bool:
    """Return whether integrity error represents duplicate room/window identity."""

    message = str(error.orig).lower()
    return (
        (
            "supervisor_summary_dispatches.room_id" in message
            and "supervisor_summary_dispatches.window_start" in message
            and "supervisor_summary_dispatches.window_end" in message
        )
        or "uq_supervisor_summary_dispatches_room_window" in message
    )


def _to_dispatch_record(row: RowMapping) -> SupervisorSummaryDispatchRecord:
    """Convert one SQLAlchemy mapping row into dispatch record dataclass."""

    return SupervisorSummaryDispatchRecord(
        dispatch_id=int(cast(int, row["id"])),
        room_id=cast(str, row["room_id"]),
        window_start=cast(datetime, row["window_start"]),
        window_end=cast(datetime, row["window_end"]),
        status=cast(SupervisorSummaryDispatchStatus, row["status"]),
        sent_at=cast(datetime | None, row["sent_at"]),
        matrix_event_id=cast(str | None, row["matrix_event_id"]),
        last_error=cast(str | None, row["last_error"]),
        created_at=cast(datetime, row["created_at"]),
        updated_at=cast(datetime, row["updated_at"]),
    )


class SqlAlchemySupervisorSummaryDispatchRepository(SupervisorSummaryDispatchRepositoryPort):
    """Idempotent Room-4 dispatch repository backed by SQLAlchemy async sessions."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def claim_window(self, payload: SupervisorSummaryWindowKey) -> bool:
        """Claim execution for one room/window, reclaiming failed rows via CAS update."""

        insert_statement = sa.insert(supervisor_summary_dispatches).values(
            room_id=payload.room_id,
            window_start=payload.window_start,
            window_end=payload.window_end,
            status="pending",
        )

        async with self._session_factory() as session:
            try:
                await session.execute(insert_statement)
                await session.commit()
                return True
            except IntegrityError as error:
                await session.rollback()
                if not _is_duplicate_room_window_error(error):
                    raise

                reclaim_statement = (
                    sa.update(supervisor_summary_dispatches)
                    .where(
                        supervisor_summary_dispatches.c.room_id == payload.room_id,
                        supervisor_summary_dispatches.c.window_start == payload.window_start,
                        supervisor_summary_dispatches.c.window_end == payload.window_end,
                        supervisor_summary_dispatches.c.status == "failed",
                    )
                    .values(
                        status="pending",
                        last_error=None,
                        updated_at=sa.func.current_timestamp(),
                    )
                )
                result = cast(CursorResult[Any], await session.execute(reclaim_statement))
                await session.commit()
                return int(result.rowcount or 0) == 1

    async def mark_sent(self, payload: SupervisorSummaryDispatchSentInput) -> bool:
        """Mark pending room/window dispatch as sent; return whether state changed."""

        statement = (
            sa.update(supervisor_summary_dispatches)
            .where(
                supervisor_summary_dispatches.c.room_id == payload.room_id,
                supervisor_summary_dispatches.c.window_start == payload.window_start,
                supervisor_summary_dispatches.c.window_end == payload.window_end,
                supervisor_summary_dispatches.c.status == "pending",
            )
            .values(
                status="sent",
                sent_at=payload.sent_at,
                matrix_event_id=payload.matrix_event_id,
                last_error=None,
                updated_at=sa.func.current_timestamp(),
            )
        )

        async with self._session_factory() as session:
            result = cast(CursorResult[Any], await session.execute(statement))
            await session.commit()

        return int(result.rowcount or 0) == 1

    async def get_by_window(
        self,
        *,
        room_id: str,
        window_start: datetime,
        window_end: datetime,
    ) -> SupervisorSummaryDispatchRecord | None:
        """Load dispatch row for room/window identity if present."""

        statement = sa.select(supervisor_summary_dispatches).where(
            supervisor_summary_dispatches.c.room_id == room_id,
            supervisor_summary_dispatches.c.window_start == window_start,
            supervisor_summary_dispatches.c.window_end == window_end,
        )

        async with self._session_factory() as session:
            result = await session.execute(statement)

        row = result.mappings().first()
        if row is None:
            return None
        return _to_dispatch_record(row)
