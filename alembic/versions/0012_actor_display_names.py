"""Add optional actor display-name columns for timeline readability."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0012_actor_display_names"
down_revision = "0011_case_reaction_checkpoints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add nullable display-name columns to transcript and reaction tables."""

    op.add_column(
        "case_matrix_message_transcripts",
        sa.Column("sender_display_name", sa.Text(), nullable=True),
    )
    op.add_column(
        "case_reaction_checkpoints",
        sa.Column("reactor_display_name", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Drop display-name columns from transcript and reaction tables."""

    op.drop_column("case_reaction_checkpoints", "reactor_display_name")
    op.drop_column("case_matrix_message_transcripts", "sender_display_name")
