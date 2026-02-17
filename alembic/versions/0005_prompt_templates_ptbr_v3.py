"""Activate Portuguese-first prompt template v3 defaults."""

from __future__ import annotations

from uuid import UUID

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0005_prompt_templates_ptbr_v3"
down_revision = "0004_prompt_templates_english_v2"
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
                "id": UUID("33333333-3333-3333-3333-333333333111"),
                "name": "llm1_system",
                "version": 3,
                "content": (
                    "Voce e um assistente clinico para triagem de Endoscopia Digestiva Alta "
                    "(EDA). Retorne APENAS JSON valido que siga estritamente o schema_version "
                    "1.1. Escreva todos os campos narrativos em portugues brasileiro (pt-BR). "
                    "Nao use palavras em ingles nos campos narrativos. Nao inclua markdown, "
                    "blocos de codigo ou chaves extras. Nao invente fatos; use null/unknown "
                    "quando faltar informacao."
                ),
                "is_active": True,
            },
            {
                "id": UUID("33333333-3333-3333-3333-333333333112"),
                "name": "llm1_user",
                "version": 3,
                "content": (
                    "Tarefa: extrair dados estruturados e gerar resumo conciso de triagem "
                    "a partir de um relatorio clinico para triagem EDA. "
                    "Nao use palavras em ingles nos campos narrativos."
                ),
                "is_active": True,
            },
            {
                "id": UUID("33333333-3333-3333-3333-333333333113"),
                "name": "llm2_system",
                "version": 3,
                "content": (
                    "Voce e um assistente de apoio a decisao clinica para triagem de "
                    "Endoscopia Digestiva Alta (EDA). Retorne APENAS JSON valido que siga "
                    "estritamente o schema_version 1.1. Escreva todos os campos narrativos em "
                    "portugues brasileiro (pt-BR). Nao use palavras em ingles nos campos "
                    "narrativos. Use apenas valores de enum permitidos para suggestion e "
                    "support_recommendation. Nao inclua markdown, blocos de codigo ou chaves "
                    "extras."
                ),
                "is_active": True,
            },
            {
                "id": UUID("33333333-3333-3333-3333-333333333114"),
                "name": "llm2_user",
                "version": 3,
                "content": (
                    "Tarefa: sugerir accept/deny e recomendacao de suporte para triagem EDA "
                    "usando dados estruturados do LLM1 e contexto de caso anterior. "
                    "Nao use palavras em ingles nos campos narrativos."
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
            "AND version = 3"
        )
    )
    op.execute(
        sa.text(
            "UPDATE prompt_templates "
            "SET is_active = TRUE "
            "WHERE name IN ('llm1_system', 'llm1_user', 'llm2_system', 'llm2_user') "
            "AND version = 2"
        )
    )
