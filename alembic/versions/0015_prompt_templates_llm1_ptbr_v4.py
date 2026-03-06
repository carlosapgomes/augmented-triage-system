"""Activate LLM1 Portuguese prompt template v4 with objective extraction constraints."""

from __future__ import annotations

from uuid import UUID

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0015_prompt_templates_llm1_ptbr_v4"
down_revision = "0014_supervisor_summary_dispatches"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE prompt_templates "
            "SET is_active = FALSE "
            "WHERE name IN ('llm1_system', 'llm1_user') "
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
                "id": UUID("44444444-4444-4444-4444-444444444111"),
                "name": "llm1_system",
                "version": 4,
                "content": (
                    "Voce e um assistente clinico para triagem de Endoscopia Digestiva Alta "
                    "(EDA). Retorne APENAS JSON valido que siga estritamente o schema_version "
                    "1.1. Escreva todos os campos narrativos em portugues brasileiro (pt-BR). "
                    "Nao use palavras em ingles nos campos narrativos. Nao inclua markdown, "
                    "blocos de codigo ou chaves extras. Nao invente fatos; use null/unknown "
                    "quando faltar informacao. Nao inferir, classificar ou estimar ASA, "
                    "Mallampati ou risco OSA."
                ),
                "is_active": True,
            },
            {
                "id": UUID("44444444-4444-4444-4444-444444444112"),
                "name": "llm1_user",
                "version": 4,
                "content": (
                    "Tarefa: extrair dados estruturados e gerar resumo conciso de triagem "
                    "a partir de um relatorio clinico para triagem EDA. Exigir evidencia "
                    "textual explicita para cada campo objetivo. Quando nao houver evidencia "
                    "textual, retornar unknown (ou null para numericos). Nao inferir, "
                    "classificar ou estimar ASA, Mallampati ou risco OSA."
                ),
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM prompt_templates "
            "WHERE name IN ('llm1_system', 'llm1_user') "
            "AND version = 4"
        )
    )
    op.execute(
        sa.text(
            "UPDATE prompt_templates "
            "SET is_active = TRUE "
            "WHERE name IN ('llm1_system', 'llm1_user') "
            "AND version = 3"
        )
    )
