"""Enforce append-only behavior for transcript persistence tables."""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0010_transcript_tables_append_only"
down_revision = "0009_transcript_case_chronological_indexes"
branch_labels = None
depends_on = None

_TRANSCRIPT_TABLES = (
    "case_report_transcripts",
    "case_llm_interactions",
    "case_matrix_message_transcripts",
)


def _create_sqlite_append_only_triggers(table_name: str) -> None:
    """Create SQLite triggers that reject UPDATE and DELETE writes."""

    op.execute(
        f"""
        CREATE TRIGGER trg_{table_name}_append_only_update
        BEFORE UPDATE ON {table_name}
        BEGIN
            SELECT RAISE(FAIL, '{table_name} is append-only');
        END
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER trg_{table_name}_append_only_delete
        BEFORE DELETE ON {table_name}
        BEGIN
            SELECT RAISE(FAIL, '{table_name} is append-only');
        END
        """
    )


def _drop_sqlite_append_only_triggers(table_name: str) -> None:
    """Drop SQLite append-only triggers for a transcript table."""

    op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_append_only_update")
    op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_append_only_delete")


def _create_postgresql_append_only_trigger(table_name: str) -> None:
    """Create PostgreSQL trigger function and trigger for append-only writes."""

    function_name = f"fn_{table_name}_append_only_guard"
    trigger_name = f"trg_{table_name}_append_only_guard"
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {function_name}()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER {trigger_name}
        BEFORE UPDATE OR DELETE ON {table_name}
        FOR EACH ROW
        EXECUTE FUNCTION {function_name}()
        """
    )


def _drop_postgresql_append_only_trigger(table_name: str) -> None:
    """Drop PostgreSQL append-only trigger and function for a table."""

    function_name = f"fn_{table_name}_append_only_guard"
    trigger_name = f"trg_{table_name}_append_only_guard"
    op.execute(f"DROP TRIGGER IF EXISTS {trigger_name} ON {table_name}")
    op.execute(f"DROP FUNCTION IF EXISTS {function_name}()")


def upgrade() -> None:
    """Apply append-only guards to transcript tables."""

    dialect_name = op.get_bind().dialect.name
    if dialect_name == "sqlite":
        for table_name in _TRANSCRIPT_TABLES:
            _create_sqlite_append_only_triggers(table_name)
        return
    if dialect_name == "postgresql":
        for table_name in _TRANSCRIPT_TABLES:
            _create_postgresql_append_only_trigger(table_name)
        return
    raise RuntimeError(
        "Unsupported database dialect for transcript append-only migration: "
        f"{dialect_name}"
    )


def downgrade() -> None:
    """Remove append-only guards from transcript tables."""

    dialect_name = op.get_bind().dialect.name
    if dialect_name == "sqlite":
        for table_name in _TRANSCRIPT_TABLES:
            _drop_sqlite_append_only_triggers(table_name)
        return
    if dialect_name == "postgresql":
        for table_name in _TRANSCRIPT_TABLES:
            _drop_postgresql_append_only_trigger(table_name)
        return
    raise RuntimeError(
        "Unsupported database dialect for transcript append-only migration: "
        f"{dialect_name}"
    )
