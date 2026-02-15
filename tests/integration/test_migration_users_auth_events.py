from __future__ import annotations

import re
from pathlib import Path

import sqlalchemy as sa
from alembic.config import Config

from alembic import command


def _upgrade_head(tmp_path: Path) -> str:
    db_path = tmp_path / "slice22_users_auth.db"
    database_url = f"sqlite+pysqlite:///{db_path}"

    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_config, "head")
    return database_url


def test_users_schema_has_unique_email_and_role_check_constraint(tmp_path: Path) -> None:
    database_url = _upgrade_head(tmp_path)
    engine = sa.create_engine(database_url)
    inspector = sa.inspect(engine)

    assert "users" in set(inspector.get_table_names())

    unique_constraints = {
        tuple(sorted(constraint["column_names"]))
        for constraint in inspector.get_unique_constraints("users")
    }
    assert ("email",) in unique_constraints

    role_checks = [
        check
        for check in inspector.get_check_constraints("users")
        if check["name"] == "ck_users_role"
    ]
    assert len(role_checks) == 1

    sqltext = str(role_checks[0].get("sqltext", ""))
    values = set(re.findall(r"'([^']+)'", sqltext))
    assert values == {"admin", "reader"}


def test_auth_events_and_auth_tokens_schema_with_expected_indexes_and_fks(tmp_path: Path) -> None:
    database_url = _upgrade_head(tmp_path)
    engine = sa.create_engine(database_url)
    inspector = sa.inspect(engine)

    assert "auth_events" in set(inspector.get_table_names())
    assert "auth_tokens" in set(inspector.get_table_names())

    auth_events_indexes = {index["name"] for index in inspector.get_indexes("auth_events")}
    assert "ix_auth_events_user_id_occurred_at" in auth_events_indexes
    assert "ix_auth_events_event_type_occurred_at" in auth_events_indexes

    auth_tokens_uniques = {
        tuple(sorted(constraint["column_names"]))
        for constraint in inspector.get_unique_constraints("auth_tokens")
    }
    assert ("token_hash",) in auth_tokens_uniques

    auth_tokens_fks = inspector.get_foreign_keys("auth_tokens")
    assert any(
        fk["referred_table"] == "users" and fk["constrained_columns"] == ["user_id"]
        for fk in auth_tokens_fks
    )


def test_prompt_templates_updated_by_user_fk_exists_after_migration(tmp_path: Path) -> None:
    database_url = _upgrade_head(tmp_path)
    engine = sa.create_engine(database_url)
    inspector = sa.inspect(engine)

    prompt_template_fks = inspector.get_foreign_keys("prompt_templates")
    assert any(
        fk["referred_table"] == "users" and fk["constrained_columns"] == ["updated_by_user_id"]
        for fk in prompt_template_fks
    )
