"""Add table to persist full extracted report text per case."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0006_case_report_transcripts"
down_revision = "0005_prompt_templates_ptbr_v3"
branch_labels = None
depends_on = None

sqlite_bigint = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "case_report_transcripts",
        sa.Column("id", sqlite_bigint, primary_key=True, autoincrement=True),
        sa.Column("case_id", sa.Uuid(), sa.ForeignKey("cases.case_id"), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade() -> None:
    op.drop_table("case_report_transcripts")
