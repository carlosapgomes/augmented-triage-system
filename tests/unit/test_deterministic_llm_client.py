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


# ---------------------------------------------------------------------------
# Slice 5.1 – Deterministic-client tests for origin, transfusion, tracked exams
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deterministic_llm1_emits_origin_context_with_city_and_state() -> None:
    """Deterministic client must populate origin_context (not just defaults)."""
    payload = await _complete_llm1(
        clinical_text="Paciente procedente de São Paulo, SP, encaminhado do Hospital das Clínicas"
    )

    validated = Llm1Response.model_validate(payload)

    assert validated.origin_context is not None
    assert validated.origin_context.city is not None
    assert validated.origin_context.state_uf is not None


@pytest.mark.asyncio
async def test_deterministic_llm1_emits_origin_context_with_hospital_and_unit() -> None:
    """Deterministic client must populate hospital/unit fields in origin_context."""
    payload = await _complete_llm1(
        clinical_text="Paciente procedente de Belo Horizonte, MG, Unidade de Emergência"
    )

    validated = Llm1Response.model_validate(payload)

    assert validated.origin_context.hospital is not None
    assert validated.origin_context.unit is not None


@pytest.mark.asyncio
async def test_deterministic_llm1_emits_transfusion_no_when_not_mentioned() -> None:
    """When clinical text has no transfusion mention, had_transfusion must be 'no'."""
    payload = await _complete_llm1(clinical_text="EDA eletiva sem menção a transfusão")

    validated = Llm1Response.model_validate(payload)

    assert validated.transfusion.had_transfusion == "no"
    assert validated.transfusion.source_text_hint is not None


@pytest.mark.asyncio
async def test_deterministic_llm1_emits_transfusion_yes_when_mentioned() -> None:
    """When clinical text mentions transfusion, had_transfusion must be 'yes'."""
    payload = await _complete_llm1(
        clinical_text="Paciente recebeu transfusão de 2 concentrados de hemácias no pré-operatório"
    )

    validated = Llm1Response.model_validate(payload)

    assert validated.transfusion.had_transfusion == "yes"
    assert validated.transfusion.total_units is not None
    assert validated.transfusion.total_units >= 1
    assert validated.transfusion.source_text_hint is not None


@pytest.mark.asyncio
async def test_deterministic_llm1_emits_tracked_exams_with_recency() -> None:
    """Deterministic client must emit tracked_exams with at least one entry and recency marker."""
    payload = await _complete_llm1(
        clinical_text="Hemoglobina 12.5 em 10/01/2024 e Hemoglobina 11.0 em 15/03/2024"
    )

    validated = Llm1Response.model_validate(payload)

    assert len(validated.tracked_exams) >= 1
    hb_exams = [
        e
        for e in validated.tracked_exams
        if "hb" in e.exam_type.lower()
        or "hemoglobina" in (e.exam_label or "").lower()
    ]
    assert len(hb_exams) >= 1, "Expected at least one hemoglobin tracked exam"
    # At least one must be marked as most recent
    assert any(e.is_most_recent for e in hb_exams)


@pytest.mark.asyncio
async def test_deterministic_llm1_tracked_exams_have_source_text_hint() -> None:
    """Every tracked exam must carry a source_text_hint."""
    payload = await _complete_llm1(
        clinical_text="Hemoglobina 11.0, Plaquetas 180.000, Creatinina 0.9"
    )

    validated = Llm1Response.model_validate(payload)

    assert len(validated.tracked_exams) >= 1
    for exam in validated.tracked_exams:
        assert exam.source_text_hint is not None
        assert exam.exam_type != ""


# ---------------------------------------------------------------------------
# Existing tests (unchanged)
# ---------------------------------------------------------------------------


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
