"""Activate english prompt template v2 defaults with pt-BR output requirement."""

from __future__ import annotations

from uuid import UUID

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0004_prompt_templates_english_v2"
down_revision = "0003_users_auth_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE prompt_templates "
            "SET is_active = FALSE "
            "WHERE name IN ('llm1_system', 'llm1_user', 'llm2_system', 'llm2_user') "
            "AND is_active IS TRUE"
        )
    )

    prompt_templates = sa.table(
        "prompt_templates",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.Text()),
        sa.column("version", sa.Integer()),
        sa.column("content", sa.Text()),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(
        prompt_templates,
        [
            {
                "id": UUID("22222222-2222-2222-2222-222222222111"),
                "name": "llm1_system",
                "version": 2,
                "content": (
                    "You are a clinical assistant for Upper GI Endoscopy (EDA) triage. "
                    "Return ONLY valid JSON that strictly matches schema_version 1.1. "
                    "Write every natural-language field in Brazilian Portuguese (pt-BR). "
                    "Do not include markdown, code fences, or extra keys. "
                    "Do not invent facts; use null/unknown when information is missing."
                ),
                "is_active": True,
            },
            {
                "id": UUID("22222222-2222-2222-2222-222222222112"),
                "name": "llm1_user",
                "version": 2,
                "content": (
                    "Task: extract structured data and generate a concise triage summary from "
                    "a clinical report for EDA triage."
                ),
                "is_active": True,
            },
            {
                "id": UUID("22222222-2222-2222-2222-222222222113"),
                "name": "llm2_system",
                "version": 2,
                "content": (
                    "You are a clinical decision-support assistant for Upper GI Endoscopy "
                    "(EDA) triage. Return ONLY valid JSON that strictly matches schema_version "
                    "1.1. Write every natural-language field in Brazilian Portuguese (pt-BR). "
                    "Use only allowed enum values for suggestion and support_recommendation. "
                    "Do not include markdown, code fences, or extra keys."
                ),
                "is_active": True,
            },
            {
                "id": UUID("22222222-2222-2222-2222-222222222114"),
                "name": "llm2_user",
                "version": 2,
                "content": (
                    "Task: suggest accept/deny and support recommendation for EDA triage "
                    "using LLM1 structured data and prior-case context."
                ),
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM prompt_templates "
            "WHERE name IN ('llm1_system', 'llm1_user', 'llm2_system', 'llm2_user') "
            "AND version = 2"
        )
    )
    op.execute(
        sa.text(
            "UPDATE prompt_templates "
            "SET is_active = TRUE "
            "WHERE name IN ('llm1_system', 'llm1_user', 'llm2_system', 'llm2_user') "
            "AND version = 1"
        )
    )
