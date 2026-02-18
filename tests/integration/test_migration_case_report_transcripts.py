from __future__ import annotations

from pathlib import Path

import sqlalchemy as sa
from alembic.config import Config

from alembic import command


def _upgrade_head(tmp_path: Path) -> str:
    db_path = tmp_path / "slice_dashboard_report_transcripts.db"
    database_url = f"sqlite+pysqlite:///{db_path}"

    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_config, "head")
    return database_url


def test_case_report_transcripts_table_exists_with_required_columns(tmp_path: Path) -> None:
    database_url = _upgrade_head(tmp_path)
    engine = sa.create_engine(database_url)
    inspector = sa.inspect(engine)

    assert "case_report_transcripts" in set(inspector.get_table_names())

    columns = {
        column["name"]: column for column in inspector.get_columns("case_report_transcripts")
    }
    assert set(columns.keys()) == {"id", "case_id", "extracted_text", "captured_at"}
    assert columns["case_id"]["nullable"] is False
    assert columns["extracted_text"]["nullable"] is False
    assert columns["captured_at"]["nullable"] is False


def test_case_report_transcripts_case_id_foreign_key_points_to_cases(tmp_path: Path) -> None:
    database_url = _upgrade_head(tmp_path)
    engine = sa.create_engine(database_url)
    inspector = sa.inspect(engine)

    foreign_keys = inspector.get_foreign_keys("case_report_transcripts")
    assert any(
        foreign_key["referred_table"] == "cases"
        and foreign_key["constrained_columns"] == ["case_id"]
        for foreign_key in foreign_keys
    )
