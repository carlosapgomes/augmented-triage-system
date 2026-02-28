"""Add Room-4 supervisor summary dispatch tracking table."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0014_supervisor_summary_dispatches"
down_revision = "0013_user_account_status"
branch_labels = None
depends_on = None

sqlite_bigint = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    """Create dispatch table with unique window identity per Room-4 target."""

    op.create_table(
        "supervisor_summary_dispatches",
        sa.Column("id", sqlite_bigint, primary_key=True, autoincrement=True),
        sa.Column("room_id", sa.Text(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("matrix_event_id", sa.Text(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'sent', 'failed')",
            name="ck_supervisor_summary_dispatches_status",
        ),
        sa.UniqueConstraint(
            "room_id",
            "window_start",
            "window_end",
            name="uq_supervisor_summary_dispatches_room_window",
        ),
    )
    op.create_index(
        "ix_supervisor_summary_dispatches_status_window_end",
        "supervisor_summary_dispatches",
        ["status", "window_end"],
        unique=False,
    )


def downgrade() -> None:
    """Drop supervisor summary dispatch tracking table and indexes."""

    op.drop_index(
        "ix_supervisor_summary_dispatches_status_window_end",
        table_name="supervisor_summary_dispatches",
    )
    op.drop_table("supervisor_summary_dispatches")
