from __future__ import annotations

import re
from pathlib import Path

import sqlalchemy as sa
from alembic.config import Config

from alembic import command


def _upgrade_head(tmp_path: Path) -> str:
    db_path = tmp_path / "slice_dashboard_llm_interactions.db"
    database_url = f"sqlite+pysqlite:///{db_path}"

    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_config, "head")
    return database_url


def test_case_llm_interactions_table_exists_with_required_columns(tmp_path: Path) -> None:
    database_url = _upgrade_head(tmp_path)
    engine = sa.create_engine(database_url)
    inspector = sa.inspect(engine)

    assert "case_llm_interactions" in set(inspector.get_table_names())

    columns = {column["name"] for column in inspector.get_columns("case_llm_interactions")}
    assert columns == {
        "id",
        "case_id",
        "stage",
        "input_payload",
        "output_payload",
        "prompt_system_name",
        "prompt_system_version",
        "prompt_user_name",
        "prompt_user_version",
        "model_name",
        "captured_at",
    }


def test_case_llm_interactions_has_case_fk_and_stage_check(tmp_path: Path) -> None:
    database_url = _upgrade_head(tmp_path)
    engine = sa.create_engine(database_url)
    inspector = sa.inspect(engine)

    foreign_keys = inspector.get_foreign_keys("case_llm_interactions")
    assert any(
        foreign_key["referred_table"] == "cases"
        and foreign_key["constrained_columns"] == ["case_id"]
        for foreign_key in foreign_keys
    )

    stage_checks = [
        check
        for check in inspector.get_check_constraints("case_llm_interactions")
        if check["name"] == "ck_case_llm_interactions_stage"
    ]
    assert len(stage_checks) == 1
    sqltext = str(stage_checks[0].get("sqltext", ""))
    values = set(re.findall(r"'([^']+)'", sqltext))
    assert values == {"LLM1", "LLM2"}
