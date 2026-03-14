from __future__ import annotations

import json

import pytest

from triage_automation.application.dto.llm1_models import Llm1Response
from triage_automation.infrastructure.llm.deterministic_client import DeterministicLlmClient


async def _complete_llm1(*, clinical_text: str) -> dict[str, object]:
    client = DeterministicLlmClient(stage="llm1")
    raw_response = await client.complete(
        system_prompt="system",
        user_prompt=(
            "agency_record_number: 12345\n\n"
            f"Texto clinico do relatorio:\n{clinical_text}"
        ),
    )
    decoded = json.loads(raw_response)
    assert isinstance(decoded, dict)
    return decoded


@pytest.mark.asyncio
async def test_deterministic_llm1_payload_matches_rewritten_schema_defaults() -> None:
    payload = await _complete_llm1(clinical_text="EDA eletiva com hemoglobina 11")

    validated = Llm1Response.model_validate(payload)

    assert validated.eda.requested_procedure.subtype == "standard"
    assert validated.eda.asa is not None
    assert validated.eda.asa.bucket == "I-II"
    assert validated.preop_screening.rulebook_signals.eda_subtype == "standard"
    assert (
        validated.preop_screening.rulebook_signals.minimum_exam_evidence.hb_numeric_present
        == "yes"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("clinical_text", "expected_subtype"),
    [
        ("pedido de EDA para gastrostomia por PEG", "gastrostomy"),
        ("solicitacao de EDA com dilatacao esofagica", "esophageal_dilation"),
        ("EDA para retirada de corpo estranho esofagico", "foreign_body"),
    ],
)
async def test_deterministic_llm1_payload_supports_all_supported_eda_subtypes(
    clinical_text: str,
    expected_subtype: str,
) -> None:
    payload = await _complete_llm1(clinical_text=clinical_text)

    validated = Llm1Response.model_validate(payload)

    assert validated.eda.requested_procedure.subtype == expected_subtype
    assert validated.preop_screening.rulebook_signals.eda_subtype == expected_subtype


@pytest.mark.asyncio
async def test_deterministic_llm1_payload_can_emit_insufficient_asa_evidence_case() -> None:
    payload = await _complete_llm1(
        clinical_text="EDA eletiva com dados insuficientes para ASA e historia clinica limitada"
    )

    validated = Llm1Response.model_validate(payload)

    assert validated.eda.asa is not None
    assert validated.eda.asa.bucket == "insufficient_data"
    assert validated.eda.cardiovascular_risk is not None
    assert validated.eda.cardiovascular_risk.level == "unknown"
