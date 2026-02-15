"""Deterministic LLM adapters for manual runtime smoke testing."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Literal

_CASE_ID_PATTERN = re.compile(r"case_id:\s*([0-9a-fA-F-]{36})")
_AGENCY_RECORD_PATTERN = re.compile(r"agency_record_number:\s*([0-9]{5})")


@dataclass(frozen=True)
class DeterministicLlmClient:
    """Deterministic stage-specific LLM client for runtime validation mode."""

    stage: Literal["llm1", "llm2"]

    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        """Return deterministic schema-valid JSON for LLM1 or LLM2 stage."""

        _ = system_prompt
        if self.stage == "llm1":
            return _build_llm1_payload(user_prompt=user_prompt)
        return _build_llm2_payload(user_prompt=user_prompt)


def _build_llm1_payload(*, user_prompt: str) -> str:
    agency_record_number = _extract_agency_record_number(user_prompt=user_prompt)
    payload = {
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
                "hb_g_dl": 11.0,
                "platelets_per_mm3": 180000,
                "inr": 1.1,
                "source_text_hint": "deterministic",
            },
            "ecg": {
                "report_present": "yes",
                "abnormal_flag": "no",
                "source_text_hint": "deterministic",
            },
            "asa": {"class": "II", "confidence": "media", "rationale": "deterministic"},
            "cardiovascular_risk": {
                "level": "low",
                "confidence": "media",
                "rationale": "deterministic",
            },
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
            "notes": "deterministic",
        },
        "summary": {
            "one_liner": "Resumo deterministico para validacao de runtime",
            "bullet_points": [
                "deterministic passo 1",
                "deterministic passo 2",
                "deterministic passo 3",
            ],
        },
        "extraction_quality": {"confidence": "media", "missing_fields": [], "notes": None},
    }
    return json.dumps(payload, ensure_ascii=False)


def _build_llm2_payload(*, user_prompt: str) -> str:
    case_id = _extract_case_id(user_prompt=user_prompt)
    agency_record_number = _extract_agency_record_number(user_prompt=user_prompt)
    payload = {
        "schema_version": "1.1",
        "language": "pt-BR",
        "case_id": case_id,
        "agency_record_number": agency_record_number,
        "suggestion": "accept",
        "support_recommendation": "none",
        "rationale": {
            "short_reason": "Deterministico: criterios minimos atendidos",
            "details": ["deterministic detalhe 1", "deterministic detalhe 2"],
            "missing_info_questions": [],
        },
        "policy_alignment": {
            "excluded_request": False,
            "labs_ok": "yes",
            "ecg_ok": "yes",
            "pediatric_flag": False,
            "notes": "deterministic",
        },
        "confidence": "media",
    }
    return json.dumps(payload, ensure_ascii=False)


def _extract_case_id(*, user_prompt: str) -> str:
    match = _CASE_ID_PATTERN.search(user_prompt)
    if match is None:
        raise ValueError("deterministic llm2 prompt missing case_id")
    return match.group(1)


def _extract_agency_record_number(*, user_prompt: str) -> str:
    match = _AGENCY_RECORD_PATTERN.search(user_prompt)
    if match is None:
        raise ValueError("deterministic llm prompt missing agency_record_number")
    return match.group(1)
