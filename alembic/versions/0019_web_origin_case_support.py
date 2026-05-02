"""web-origin case support: add origin_source, web_pdf columns, nullable matrix fields.

Revision ID: 0019
Revises: 0018
Create Date: 2026-05-01
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "0019_web_origin_case_support"
down_revision = "0018_prompt_templates_llm1_ptbr_v6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add web-origin columns and relax Matrix-origin constraints."""

    with op.batch_alter_table("cases", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "origin_source",
                sa.Text(),
                nullable=False,
                server_default=sa.text("'matrix'"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "web_pdf_filename",
                sa.Text(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "web_pdf_storage_path",
                sa.Text(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "web_uploaded_by_user_id",
                sa.Text(),
                nullable=True,
            )
        )
        batch_op.alter_column(
            "room1_origin_room_id",
            existing_type=sa.Text(),
            nullable=True,
        )
        batch_op.alter_column(
            "room1_origin_event_id",
            existing_type=sa.Text(),
            nullable=True,
        )
        batch_op.alter_column(
            "room1_sender_user_id",
            existing_type=sa.Text(),
            nullable=True,
        )


def downgrade() -> None:
    """Revert to Matrix-only case origins."""

    with op.batch_alter_table("cases", schema=None) as batch_op:
        batch_op.alter_column(
            "room1_sender_user_id",
            existing_type=sa.Text(),
            nullable=False,
        )
        batch_op.alter_column(
            "room1_origin_event_id",
            existing_type=sa.Text(),
            nullable=False,
        )
        batch_op.alter_column(
            "room1_origin_room_id",
            existing_type=sa.Text(),
            nullable=False,
        )
        batch_op.drop_column("web_uploaded_by_user_id")
        batch_op.drop_column("web_pdf_storage_path")
        batch_op.drop_column("web_pdf_filename")
        batch_op.drop_column("origin_source")
