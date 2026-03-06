from __future__ import annotations

import json
from uuid import uuid4

import pytest

from triage_automation.application.services.llm1_service import (
    Llm1RetriableError,
    Llm1Service,
)


class FakeLlmClient:
    def __init__(self, response_text: str | list[str]) -> None:
        if isinstance(response_text, list):
            self._responses = response_text
        else:
            self._responses = [response_text]
        self.calls: list[tuple[str, str]] = []

    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        if len(self._responses) == 1:
            return self._responses[0]
        return self._responses.pop(0)


def _valid_llm1_payload(agency_record_number: str) -> dict[str, object]:
    return {
        "schema_version": "1.1",
        "language": "pt-BR",
        "agency_record_number": agency_record_number,
        "patient": {
            "name": "Paciente",
            "age": 45,
            "sex": "F",
            "document_id": None,
        },
        "eda": {
            "indication_category": "dyspepsia",
            "exclusion_type": "none",
            "is_pediatric": False,
            "foreign_body_suspected": False,
            "requested_procedure": {
                "name": "EDA",
                "urgency": "eletivo",
            },
            "labs": {
                "hb_g_dl": 10.2,
                "platelets_per_mm3": 140000,
                "inr": 1.1,
                "source_text_hint": None,
            },
            "ecg": {
                "report_present": "yes",
                "abnormal_flag": "no",
                "source_text_hint": None,
            },
        },
        "preop_screening": {
            "exam_type": "eda",
            "has_cardiovascular_disease": "no",
            "has_active_respiratory_symptoms": "no",
            "has_prior_respiratory_disease": "no",
            "has_ecg_report": "yes",
            "has_chest_xray_report": "yes",
            "hb_g_dl": 10.2,
            "platelets_per_mm3": 140000,
            "inr": 1.1,
        },
        "policy_precheck": {
            "excluded_from_eda_flow": False,
            "exclusion_reason": None,
            "labs_required": True,
            "labs_pass": "yes",
            "labs_failed_items": [],
            "ecg_required": True,
            "ecg_present": "yes",
            "pediatric_flag": False,
            "notes": None,
        },
        "summary": {
            "one_liner": "Resumo clinico",
            "bullet_points": ["ponto 1", "ponto 2", "ponto 3"],
        },
        "extraction_quality": {
            "confidence": "media",
            "missing_fields": [],
            "notes": None,
        },
    }


def _with_preop_screening(
    payload: dict[str, object],
    *,
    exam_type: str,
    has_cardiovascular_disease: str,
    has_active_respiratory_symptoms: str,
    has_prior_respiratory_disease: str,
    has_ecg_report: str,
    has_chest_xray_report: str,
    hb_g_dl: float | None,
    platelets_per_mm3: int | None,
    inr: float | None,
    evidence_spans: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    payload["preop_screening"] = {
        "exam_type": exam_type,
        "has_cardiovascular_disease": has_cardiovascular_disease,
        "has_active_respiratory_symptoms": has_active_respiratory_symptoms,
        "has_prior_respiratory_disease": has_prior_respiratory_disease,
        "has_ecg_report": has_ecg_report,
        "has_chest_xray_report": has_chest_xray_report,
        "hb_g_dl": hb_g_dl,
        "platelets_per_mm3": platelets_per_mm3,
        "inr": inr,
        "evidence_spans": evidence_spans or [],
    }
    return payload


@pytest.mark.asyncio
async def test_valid_llm1_response_parses_and_returns_artifacts() -> None:
    agency_record = "12345"
    client = FakeLlmClient(json.dumps(_valid_llm1_payload(agency_record)))
    service = Llm1Service(llm_client=client)

    result = await service.run(
        case_id=uuid4(),
        agency_record_number=agency_record,
        clean_text="texto limpo",
    )

    assert result.summary_text == "Resumo clinico"
    assert result.structured_data_json["agency_record_number"] == agency_record


@pytest.mark.asyncio
async def test_llm1_extracts_preop_screening_scope_and_risk_fields() -> None:
    agency_record = "12345"
    payload = _with_preop_screening(
        _valid_llm1_payload(agency_record),
        exam_type="eda",
        has_cardiovascular_disease="yes",
        has_active_respiratory_symptoms="no",
        has_prior_respiratory_disease="unknown",
        has_ecg_report="yes",
        has_chest_xray_report="no",
        hb_g_dl=10.2,
        platelets_per_mm3=140000,
        inr=1.1,
    )
    client = FakeLlmClient(json.dumps(payload))
    service = Llm1Service(llm_client=client)

    try:
        result = await service.run(
            case_id=uuid4(),
            agency_record_number=agency_record,
            clean_text="texto limpo",
        )
    except Llm1RetriableError as error:
        pytest.fail(f"unexpected LLM1 validation failure: {error}")

    assert result.structured_data_json["preop_screening"] == {
        "exam_type": "eda",
        "has_cardiovascular_disease": "yes",
        "has_active_respiratory_symptoms": "no",
        "has_prior_respiratory_disease": "unknown",
        "has_ecg_report": "yes",
        "has_chest_xray_report": "no",
        "hb_g_dl": 10.2,
        "platelets_per_mm3": 140000,
        "inr": 1.1,
        "evidence_spans": [],
    }


@pytest.mark.asyncio
async def test_llm1_preop_screening_accepts_unknown_fallback_values() -> None:
    agency_record = "12345"
    payload = _with_preop_screening(
        _valid_llm1_payload(agency_record),
        exam_type="unknown",
        has_cardiovascular_disease="unknown",
        has_active_respiratory_symptoms="unknown",
        has_prior_respiratory_disease="unknown",
        has_ecg_report="unknown",
        has_chest_xray_report="unknown",
        hb_g_dl=None,
        platelets_per_mm3=None,
        inr=None,
    )
    client = FakeLlmClient(json.dumps(payload))
    service = Llm1Service(llm_client=client)

    try:
        result = await service.run(
            case_id=uuid4(),
            agency_record_number=agency_record,
            clean_text="texto sem evidencias objetivas",
        )
    except Llm1RetriableError as error:
        pytest.fail(f"unexpected LLM1 validation failure: {error}")

    assert result.structured_data_json["preop_screening"] == {
        "exam_type": "unknown",
        "has_cardiovascular_disease": "unknown",
        "has_active_respiratory_symptoms": "unknown",
        "has_prior_respiratory_disease": "unknown",
        "has_ecg_report": "unknown",
        "has_chest_xray_report": "unknown",
        "hb_g_dl": None,
        "platelets_per_mm3": None,
        "inr": None,
        "evidence_spans": [],
    }


@pytest.mark.asyncio
async def test_llm1_preop_screening_preserves_evidence_spans() -> None:
    agency_record = "12345"
    payload = _with_preop_screening(
        _valid_llm1_payload(agency_record),
        exam_type="eda",
        has_cardiovascular_disease="yes",
        has_active_respiratory_symptoms="no",
        has_prior_respiratory_disease="unknown",
        has_ecg_report="yes",
        has_chest_xray_report="unknown",
        hb_g_dl=9.8,
        platelets_per_mm3=125000,
        inr=1.3,
        evidence_spans=[
            {
                "field_path": "preop_screening.has_cardiovascular_disease",
                "excerpt": "historia de cardiopatia hipertensiva",
            },
            {
                "field_path": "preop_screening.has_ecg_report",
                "excerpt": "eletrocardiograma anexo",
            },
        ],
    )
    client = FakeLlmClient(json.dumps(payload))
    service = Llm1Service(llm_client=client)

    result = await service.run(
        case_id=uuid4(),
        agency_record_number=agency_record,
        clean_text="texto limpo",
    )

    assert result.structured_data_json["preop_screening"]["evidence_spans"] == [
        {
            "field_path": "preop_screening.has_cardiovascular_disease",
            "excerpt": "historia de cardiopatia hipertensiva",
        },
        {
            "field_path": "preop_screening.has_ecg_report",
            "excerpt": "eletrocardiograma anexo",
        },
    ]


@pytest.mark.asyncio
async def test_invalid_schema_is_retriable_llm1_error() -> None:
    client = FakeLlmClient(json.dumps({"schema_version": "1.1"}))
    service = Llm1Service(llm_client=client)

    with pytest.raises(Llm1RetriableError) as exc_info:
        await service.run(case_id=uuid4(), agency_record_number="12345", clean_text="texto")

    assert exc_info.value.cause == "llm1"


@pytest.mark.asyncio
async def test_non_json_response_is_rejected() -> None:
    client = FakeLlmClient("not-json")
    service = Llm1Service(llm_client=client)

    with pytest.raises(Llm1RetriableError) as exc_info:
        await service.run(case_id=uuid4(), agency_record_number="12345", clean_text="texto")

    assert exc_info.value.cause == "llm1"


@pytest.mark.asyncio
async def test_fenced_json_response_is_accepted() -> None:
    agency_record = "54321"
    payload = _valid_llm1_payload(agency_record)
    client = FakeLlmClient(f"```json\n{json.dumps(payload)}\n```")
    service = Llm1Service(llm_client=client)

    result = await service.run(
        case_id=uuid4(),
        agency_record_number=agency_record,
        clean_text="texto limpo",
    )

    assert result.structured_data_json["agency_record_number"] == agency_record


@pytest.mark.asyncio
async def test_agency_record_number_is_injected_exactly_into_prompt() -> None:
    agency_record = "54321"
    client = FakeLlmClient(json.dumps(_valid_llm1_payload(agency_record)))
    service = Llm1Service(llm_client=client)

    await service.run(
        case_id=uuid4(),
        agency_record_number=agency_record,
        clean_text="texto limpo",
    )

    assert len(client.calls) == 1
    _, user_prompt = client.calls[0]
    assert f"agency_record_number: {agency_record}" in user_prompt


@pytest.mark.asyncio
async def test_llm1_prompt_requires_textual_evidence_and_forbids_asa_mallampati_osa() -> None:
    agency_record = "54321"
    client = FakeLlmClient(json.dumps(_valid_llm1_payload(agency_record)))
    service = Llm1Service(llm_client=client)

    await service.run(
        case_id=uuid4(),
        agency_record_number=agency_record,
        clean_text="texto limpo",
    )

    system_prompt, user_prompt = client.calls[0]
    lowered_system = system_prompt.lower()
    lowered_user = user_prompt.lower()

    assert "nao inferir" in lowered_system
    assert "asa" in lowered_system
    assert "mallampati" in lowered_system
    assert "osa" in lowered_system
    assert "evidencia textual" in lowered_user
    assert "unknown" in lowered_user
    assert "evidence_spans" in lowered_user


@pytest.mark.asyncio
async def test_llm1_retries_once_when_narrative_contains_english_terms() -> None:
    agency_record = "12345"
    invalid_payload = _valid_llm1_payload(agency_record)
    invalid_payload["summary"] = {
        "one_liner": "Patient denied for criteria mismatch",
        "bullet_points": ["ponto 1", "ponto 2", "ponto 3"],
    }
    valid_payload = _valid_llm1_payload(agency_record)
    valid_payload["summary"] = {
        "one_liner": "Paciente negado por criterio clinico",
        "bullet_points": ["ponto 1", "ponto 2", "ponto 3"],
    }
    client = FakeLlmClient([json.dumps(invalid_payload), json.dumps(valid_payload)])
    service = Llm1Service(llm_client=client)

    result = await service.run(
        case_id=uuid4(),
        agency_record_number=agency_record,
        clean_text="texto limpo",
    )

    assert result.summary_text == "Paciente negado por criterio clinico"
    assert len(client.calls) == 2


@pytest.mark.asyncio
async def test_llm1_fails_when_english_terms_persist_after_retry() -> None:
    agency_record = "12345"
    invalid_payload = _valid_llm1_payload(agency_record)
    invalid_payload["summary"] = {
        "one_liner": "Patient denied for criteria mismatch",
        "bullet_points": ["ponto 1", "ponto 2", "ponto 3"],
    }
    client = FakeLlmClient([json.dumps(invalid_payload), json.dumps(invalid_payload)])
    service = Llm1Service(llm_client=client)

    with pytest.raises(Llm1RetriableError) as error_info:
        await service.run(
            case_id=uuid4(),
            agency_record_number=agency_record,
            clean_text="texto limpo",
        )

    assert error_info.value.cause == "llm1"
    assert "non-ptbr narrative terms" in error_info.value.details
    assert len(client.calls) == 2
