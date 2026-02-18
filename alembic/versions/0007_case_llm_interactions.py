"""Add table to persist complete LLM interaction payloads per case."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0007_case_llm_interactions"
down_revision = "0006_case_report_transcripts"
branch_labels = None
depends_on = None

sqlite_bigint = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "case_llm_interactions",
        sa.Column("id", sqlite_bigint, primary_key=True, autoincrement=True),
        sa.Column("case_id", sa.Uuid(), sa.ForeignKey("cases.case_id"), nullable=False),
        sa.Column("stage", sa.Text(), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("output_payload", sa.JSON(), nullable=False),
        sa.Column("prompt_system_name", sa.Text(), nullable=True),
        sa.Column("prompt_system_version", sa.Integer(), nullable=True),
        sa.Column("prompt_user_name", sa.Text(), nullable=True),
        sa.Column("prompt_user_version", sa.Integer(), nullable=True),
        sa.Column("model_name", sa.Text(), nullable=True),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "stage IN ('LLM1', 'LLM2')",
            name="ck_case_llm_interactions_stage",
        ),
    )


def downgrade() -> None:
    op.drop_table("case_llm_interactions")
