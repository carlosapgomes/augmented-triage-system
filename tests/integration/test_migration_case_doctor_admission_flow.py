from __future__ import annotations

import re
from pathlib import Path

import sqlalchemy as sa
from alembic.config import Config

from alembic import command


def _upgrade_head(tmp_path: Path) -> str:
    db_path = tmp_path / "slice_case_doctor_admission_flow.db"
    database_url = f"sqlite+pysqlite:///{db_path}"

    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_config, "head")
    return database_url


def test_cases_table_includes_doctor_admission_flow_column(tmp_path: Path) -> None:
    database_url = _upgrade_head(tmp_path)
    engine = sa.create_engine(database_url)
    inspector = sa.inspect(engine)

    columns = {column["name"] for column in inspector.get_columns("cases")}

    assert "doctor_admission_flow" in columns


def test_cases_table_restricts_doctor_admission_flow_to_normalized_values(
    tmp_path: Path,
) -> None:
    database_url = _upgrade_head(tmp_path)
    engine = sa.create_engine(database_url)
    inspector = sa.inspect(engine)

    matching_checks = [
        check
        for check in inspector.get_check_constraints("cases")
        if check["name"] == "ck_cases_doctor_admission_flow"
    ]

    assert len(matching_checks) == 1
    sqltext = str(matching_checks[0].get("sqltext", ""))
    values = set(re.findall(r"'([^']+)'", sqltext))
    assert values == {"immediate", "scheduled"}
