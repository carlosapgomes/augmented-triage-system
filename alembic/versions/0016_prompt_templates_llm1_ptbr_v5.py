"""Activate LLM1 Portuguese prompt template v5 for the rewritten EDA rulebook."""

from __future__ import annotations

from uuid import UUID

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0016_prompt_templates_llm1_ptbr_v5"
down_revision = "0015_prompt_templates_llm1_ptbr_v4"
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
                "id": UUID("55555555-5555-5555-5555-555555555111"),
                "name": "llm1_system",
                "version": 5,
                "content": (
                    "Voce e um assistente clinico para triagem de Endoscopia Digestiva Alta "
                    "(EDA). Retorne APENAS JSON valido que siga estritamente o schema_version "
                    "1.1. Escreva todos os campos narrativos em portugues brasileiro (pt-BR). "
                    "Nao use palavras em ingles nos campos narrativos. Nao inclua markdown, "
                    "blocos de codigo ou chaves extras. Nao invente fatos; use null/unknown "
                    "quando faltar informacao. Classifique o procedimento EDA suportado com "
                    "subtype em standard, gastrostomy, esophageal_dilation ou foreign_body. "
                    "Estime ASA pratico apenas nos buckets I-II, III ou mais, ou "
                    "insufficient_data, sempre de forma conservadora e baseada no texto. "
                    "Nao inferir Mallampati ou risco OSA."
                ),
                "is_active": True,
            },
            {
                "id": UUID("55555555-5555-5555-5555-555555555112"),
                "name": "llm1_user",
                "version": 5,
                "content": (
                    "Tarefa: extrair dados estruturados e gerar resumo conciso de triagem "
                    "a partir de um relatorio clinico para triagem EDA. Exigir evidencia "
                    "textual explicita para cada campo objetivo. Quando nao houver evidencia "
                    "textual, retornar unknown (ou null para numericos). Preencher "
                    "preop_screening.rulebook_signals para o novo rulebook, incluindo exames "
                    "minimos, exames condicionais, subtipo EDA suportado e contexto de "
                    "paciente pediatrico. Incluir preop_screening.evidence_spans com "
                    "field_path e excerpt sempre que houver evidencia."
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
            "AND version = 5"
        )
    )
    op.execute(
        sa.text(
            "UPDATE prompt_templates "
            "SET is_active = TRUE "
            "WHERE name IN ('llm1_system', 'llm1_user') "
            "AND version = 4"
        )
    )
