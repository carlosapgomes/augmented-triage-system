from __future__ import annotations

import json
from uuid import uuid4

import pytest

from triage_automation.application.services.llm2_service import (
    Llm2RetriableError,
    Llm2Service,
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
        "patient": {"name": "Paciente", "age": 50, "sex": "F", "document_id": None},
        "eda": {
            "indication_category": "dyspepsia",
            "exclusion_type": "none",
            "is_pediatric": False,
            "foreign_body_suspected": False,
            "requested_procedure": {"name": "EDA", "urgency": "eletivo"},
            "labs": {
                "hb_g_dl": 10.5,
                "platelets_per_mm3": 130000,
                "inr": 1.2,
                "source_text_hint": None,
            },
            "ecg": {
                "report_present": "yes",
                "abnormal_flag": "no",
                "source_text_hint": None,
            },
            "asa": {"class": "II", "confidence": "media", "rationale": None},
            "cardiovascular_risk": {"level": "low", "confidence": "media", "rationale": None},
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
        "summary": {"one_liner": "Resumo LLM1", "bullet_points": ["a", "b", "c"]},
        "extraction_quality": {"confidence": "media", "missing_fields": [], "notes": None},
    }


def _valid_llm2_payload(case_id: str, agency_record_number: str) -> dict[str, object]:
    return {
        "schema_version": "1.1",
        "language": "pt-BR",
        "case_id": case_id,
        "agency_record_number": agency_record_number,
        "suggestion": "accept",
        "support_recommendation": "none",
        "rationale": {
            "short_reason": "Apto para fluxo padrao",
            "details": ["criterio 1", "criterio 2"],
            "missing_info_questions": [],
        },
        "policy_alignment": {
            "excluded_request": False,
            "labs_ok": "yes",
            "ecg_ok": "yes",
            "pediatric_flag": False,
            "notes": None,
        },
        "confidence": "media",
    }


@pytest.mark.asyncio
async def test_llm2_retries_once_when_narrative_contains_english_terms() -> None:
    case_id = uuid4()
    agency_record_number = "12345"
    invalid_payload = _valid_llm2_payload(str(case_id), agency_record_number)
    invalid_payload["rationale"] = {
        "short_reason": "Denied by guideline mismatch",
        "details": ["criterio 1", "criterio 2"],
        "missing_info_questions": [],
    }
    valid_payload = _valid_llm2_payload(str(case_id), agency_record_number)
    valid_payload["rationale"] = {
        "short_reason": "Negado por divergencia de diretriz",
        "details": ["criterio 1", "criterio 2"],
        "missing_info_questions": [],
    }
    client = FakeLlmClient([json.dumps(invalid_payload), json.dumps(valid_payload)])
    service = Llm2Service(llm_client=client)

    result = await service.run(
        case_id=case_id,
        agency_record_number=agency_record_number,
        llm1_structured_data=_valid_llm1_payload(agency_record_number),
    )

    assert result.suggested_action_json["case_id"] == str(case_id)
    assert len(client.calls) == 2


@pytest.mark.asyncio
async def test_llm2_fails_when_english_terms_persist_after_retry() -> None:
    case_id = uuid4()
    agency_record_number = "12345"
    invalid_payload = _valid_llm2_payload(str(case_id), agency_record_number)
    invalid_payload["rationale"] = {
        "short_reason": "Denied by guideline mismatch",
        "details": ["criterio 1", "criterio 2"],
        "missing_info_questions": [],
    }
    client = FakeLlmClient([json.dumps(invalid_payload), json.dumps(invalid_payload)])
    service = Llm2Service(llm_client=client)

    with pytest.raises(Llm2RetriableError) as error_info:
        await service.run(
            case_id=case_id,
            agency_record_number=agency_record_number,
            llm1_structured_data=_valid_llm1_payload(agency_record_number),
        )

    assert error_info.value.cause == "llm2"
    assert "non-ptbr narrative terms" in error_info.value.details
    assert len(client.calls) == 2
