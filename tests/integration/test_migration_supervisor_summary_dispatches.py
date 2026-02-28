from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.config import Config

from alembic import command


def _upgrade_head(tmp_path: Path) -> str:
    db_path = tmp_path / "slice_room4_summary_dispatches.db"
    database_url = f"sqlite+pysqlite:///{db_path}"

    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_config, "head")

    return database_url


def test_supervisor_summary_dispatches_table_has_unique_window_identity(
    tmp_path: Path,
) -> None:
    database_url = _upgrade_head(tmp_path)
    engine = sa.create_engine(database_url)
    inspector = sa.inspect(engine)

    table_names = set(inspector.get_table_names())
    assert "supervisor_summary_dispatches" in table_names

    uniques = {
        tuple(sorted(constraint["column_names"]))
        for constraint in inspector.get_unique_constraints("supervisor_summary_dispatches")
    }
    assert ("room_id", "window_end", "window_start") in uniques


def test_supervisor_summary_dispatches_rejects_duplicate_window_for_same_room(
    tmp_path: Path,
) -> None:
    database_url = _upgrade_head(tmp_path)
    engine = sa.create_engine(database_url)

    window_start = datetime(2026, 2, 15, 19, 0, tzinfo=UTC)
    window_end = datetime(2026, 2, 16, 7, 0, tzinfo=UTC)

    insert_statement = sa.text(
        """
        INSERT INTO supervisor_summary_dispatches (
            room_id,
            window_start,
            window_end,
            status,
            sent_at,
            matrix_event_id,
            last_error
        ) VALUES (
            :room_id,
            :window_start,
            :window_end,
            :status,
            :sent_at,
            :matrix_event_id,
            :last_error
        )
        """
    )

    with engine.begin() as connection:
        connection.execute(
            insert_statement,
            {
                "room_id": "!room4:example.org",
                "window_start": window_start,
                "window_end": window_end,
                "status": "sent",
                "sent_at": window_end,
                "matrix_event_id": "$room4-summary-1",
                "last_error": None,
            },
        )

        with pytest.raises(sa.exc.IntegrityError):
            connection.execute(
                insert_statement,
                {
                    "room_id": "!room4:example.org",
                    "window_start": window_start,
                    "window_end": window_end,
                    "status": "sent",
                    "sent_at": window_end,
                    "matrix_event_id": "$room4-summary-2",
                    "last_error": None,
                },
            )
