from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.config import Config

from alembic import command


def _upgrade_head(tmp_path: Path) -> str:
    db_path = tmp_path / "slice_dashboard_transcript_append_only.db"
    database_url = f"sqlite+pysqlite:///{db_path}"

    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_config, "head")
    return database_url


def _insert_minimal_case(connection: sa.Connection) -> str:
    case_id = uuid4().hex
    connection.execute(
        sa.text(
            "INSERT INTO cases ("
            "case_id, status, room1_origin_room_id, room1_origin_event_id, room1_sender_user_id"
            ") VALUES ("
            ":case_id, 'NEW', '!room1:example.org', :origin_event_id, '@human:example.org'"
            ")"
        ),
        {
            "case_id": case_id,
            "origin_event_id": f"$origin-{case_id}",
        },
    )
    return case_id


@pytest.mark.parametrize(
    ("table_name", "insert_sql", "insert_params"),
    [
        (
            "case_report_transcripts",
            (
                "INSERT INTO case_report_transcripts (case_id, extracted_text) "
                "VALUES (:case_id, :extracted_text)"
            ),
            {"extracted_text": "texto do relatorio"},
        ),
        (
            "case_llm_interactions",
            (
                "INSERT INTO case_llm_interactions ("
                "case_id, stage, input_payload, output_payload, "
                "prompt_system_name, prompt_system_version, "
                "prompt_user_name, prompt_user_version, model_name"
                ") VALUES ("
                ":case_id, 'LLM1', '{\"system_prompt\":\"a\",\"user_prompt\":\"b\"}', "
                "'{\"raw_response\":\"{}\"}', "
                "'llm1_system', 1, 'llm1_user', 1, 'gpt-4o-mini'"
                ")"
            ),
            {},
        ),
        (
            "case_matrix_message_transcripts",
            (
                "INSERT INTO case_matrix_message_transcripts ("
                "case_id, room_id, event_id, sender, message_type, message_text, reply_to_event_id"
                ") VALUES ("
                ":case_id, '!room2:example.org', '$event-1', '@doctor:example.org', "
                "'room2_doctor_reply', 'decisao: aceitar', '$root-1'"
                ")"
            ),
            {},
        ),
    ],
)
def test_transcript_tables_are_append_only(
    tmp_path: Path,
    table_name: str,
    insert_sql: str,
    insert_params: dict[str, str],
) -> None:
    database_url = _upgrade_head(tmp_path)
    engine = sa.create_engine(database_url)

    with engine.begin() as connection:
        case_id = _insert_minimal_case(connection)
        connection.execute(sa.text(insert_sql), {"case_id": case_id, **insert_params})

    with engine.begin() as connection:
        with pytest.raises(sa.exc.DBAPIError):
            connection.execute(
                sa.text(
                    "UPDATE "
                    f"{table_name} "
                    "SET captured_at = CURRENT_TIMESTAMP "
                    "WHERE case_id = :case_id"
                ),
                {"case_id": case_id},
            )

    with engine.begin() as connection:
        with pytest.raises(sa.exc.DBAPIError):
            connection.execute(
                sa.text(f"DELETE FROM {table_name} WHERE case_id = :case_id"),
                {"case_id": case_id},
            )
