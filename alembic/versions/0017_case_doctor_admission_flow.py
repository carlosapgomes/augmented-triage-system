"""Add persisted doctor admission-flow column for accepted Room-2 decisions."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0017_case_doctor_admission_flow"
down_revision = "0016_prompt_templates_llm1_ptbr_v5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add nullable normalized admission-flow storage to case rows."""

    op.add_column(
        "cases",
        sa.Column("doctor_admission_flow", sa.Text(), nullable=True),
    )
    with op.batch_alter_table("cases") as batch_op:
        batch_op.create_check_constraint(
            "ck_cases_doctor_admission_flow",
            "doctor_admission_flow IS NULL OR doctor_admission_flow IN ('scheduled', 'immediate')",
        )


def downgrade() -> None:
    """Remove normalized admission-flow storage from case rows."""

    with op.batch_alter_table("cases") as batch_op:
        batch_op.drop_constraint("ck_cases_doctor_admission_flow", type_="check")
        batch_op.drop_column("doctor_admission_flow")
