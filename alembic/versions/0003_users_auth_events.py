"""Add users, auth_events, auth_tokens and prompt_templates user FK."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0003_users_auth_events"
down_revision = "0002_prompt_templates"
branch_labels = None
depends_on = None

sqlite_bigint = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint("role IN ('admin', 'reader')", name="ck_users_role"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)

    op.create_table(
        "auth_events",
        sa.Column("id", sqlite_bigint, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("ip_address", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_auth_events_user_id_occurred_at",
        "auth_events",
        ["user_id", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_auth_events_event_type_occurred_at",
        "auth_events",
        ["event_type", "occurred_at"],
        unique=False,
    )

    op.create_table(
        "auth_tokens",
        sa.Column("id", sqlite_bigint, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("token_hash", name="uq_auth_tokens_token_hash"),
    )
    op.create_index("ix_auth_tokens_user_id", "auth_tokens", ["user_id"], unique=False)
    op.create_index("ix_auth_tokens_expires_at", "auth_tokens", ["expires_at"], unique=False)

    with op.batch_alter_table("prompt_templates", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_prompt_templates_updated_by_user_id_users",
            "users",
            ["updated_by_user_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("prompt_templates", schema=None) as batch_op:
        batch_op.drop_constraint("fk_prompt_templates_updated_by_user_id_users", type_="foreignkey")

    op.drop_index("ix_auth_tokens_expires_at", table_name="auth_tokens")
    op.drop_index("ix_auth_tokens_user_id", table_name="auth_tokens")
    op.drop_table("auth_tokens")

    op.drop_index("ix_auth_events_event_type_occurred_at", table_name="auth_events")
    op.drop_index("ix_auth_events_user_id_occurred_at", table_name="auth_events")
    op.drop_table("auth_events")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
