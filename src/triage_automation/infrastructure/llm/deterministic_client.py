"""Deterministic LLM adapters for manual runtime smoke testing."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Literal

_CASE_ID_PATTERN = re.compile(r"case_id:\s*([0-9a-fA-F-]{36})")
_AGENCY_RECORD_PATTERN = re.compile(r"agency_record_number:\s*([0-9]{5,})")
_AGE_PATTERN = re.compile(r"\b(\d{1,3})\s+anos?\b", re.IGNORECASE)
_FOREIGN_BODY_PATTERN = re.compile(r"corpo\s+estranho", re.IGNORECASE)
_GASTROSTOMY_PATTERN = re.compile(r"\b(gastrostomia|gtt|peg)\b", re.IGNORECASE)
_ESOPHAGEAL_DILATION_PATTERN = re.compile(r"dilat(?:acao|ação)\s+esofagica", re.IGNORECASE)
_INSUFFICIENT_ASA_PATTERN = re.compile(
    r"dados\s+insuficientes\s+para\s+asa|historia\s+clinica\s+limitada",
    re.IGNORECASE,
)
_HIGH_RISK_PATTERN = re.compile(
    r"cardiopatia|angioplastia|iam|infarto|insuficiencia\s+cardiaca|dispneia",
    re.IGNORECASE,
)


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
    clinical_text = _extract_clinical_text(user_prompt=user_prompt)
    subtype = _detect_eda_subtype(clinical_text=clinical_text)
    age = _extract_age(clinical_text=clinical_text)
    is_pediatric = age < 16
    asa_bucket = _detect_asa_bucket(clinical_text=clinical_text)
    cardiovascular_risk = _detect_cardiovascular_risk(
        clinical_text=clinical_text,
        asa_bucket=asa_bucket,
    )
    payload = {
        "schema_version": "1.1",
        "language": "pt-BR",
        "agency_record_number": agency_record_number,
        "patient": {
            "name": "Paciente",
            "age": age,
            "sex": "F",
            "document_id": None,
        },
        "eda": {
            "indication_category": "foreign_body" if subtype == "foreign_body" else "dyspepsia",
            "exclusion_type": "none",
            "is_pediatric": is_pediatric,
            "foreign_body_suspected": subtype == "foreign_body",
            "requested_procedure": {
                "name": _canonical_procedure_name(subtype=subtype),
                "urgency": "eletivo",
                "subtype": subtype,
            },
            "labs": {
                "hb_g_dl": 11.0,
                "hct_percent": 33.0,
                "platelets_per_mm3": 180000,
                "tp_seconds": 12.4,
                "inr": 1.1,
                "rni": 1.1,
                "ttpa_seconds": 31.0,
                "urea_mg_dl": 28.0,
                "creatinine_mg_dl": 0.9,
                "source_text_hint": "deterministico",
            },
            "ecg": {
                "report_present": "yes",
                "abnormal_flag": "no",
                "source_text_hint": "deterministico",
            },
            "asa": {
                "bucket": asa_bucket,
                "source_text_hint": _asa_source_hint(asa_bucket=asa_bucket),
            },
            "cardiovascular_risk": {
                "level": cardiovascular_risk,
                "source_text_hint": _cardiovascular_risk_source_hint(
                    cardiovascular_risk=cardiovascular_risk
                ),
            },
        },
        "preop_screening": {
            "exam_type": "eda",
            "has_cardiovascular_disease": (
                "yes" if cardiovascular_risk == "moderate_high" else "no"
            ),
            "has_active_respiratory_symptoms": "no",
            "has_prior_respiratory_disease": "no",
            "has_ecg_report": "yes",
            "has_chest_xray_report": "yes",
            "has_echocardiogram_report": "yes",
            "hb_g_dl": 11.0,
            "platelets_per_mm3": 180000,
            "inr": 1.1,
            "evidence_spans": [
                {
                    "field_path": "preop_screening.rulebook_signals.eda_subtype",
                    "excerpt": _canonical_procedure_name(subtype=subtype),
                }
            ],
            "rulebook_signals": {
                "eda_subtype": subtype,
                "minimum_exam_evidence": _build_minimum_exam_evidence(subtype=subtype),
                "conditional_exam_requirements": _build_conditional_exam_requirements(
                    subtype=subtype
                ),
                "clinical_flags": _build_clinical_flags(
                    is_pediatric=is_pediatric,
                    cardiovascular_risk=cardiovascular_risk,
                ),
            },
        },
        "policy_precheck": {
            "excluded_from_eda_flow": False,
            "exclusion_reason": None,
            "labs_required": subtype != "foreign_body",
            "labs_pass": "yes" if subtype != "foreign_body" else "unknown",
            "labs_failed_items": [],
            "ecg_required": subtype != "foreign_body",
            "ecg_present": "yes" if subtype != "foreign_body" else "unknown",
            "pediatric_flag": is_pediatric,
            "notes": "deterministico",
        },
        "summary": {
            "one_liner": "Resumo deterministico para validacao de runtime",
            "bullet_points": [
                "procedimento identificado de forma deterministica",
                f"subtipo: {subtype}",
                f"asa pratico: {asa_bucket}",
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
            "details": ["deterministico detalhe 1", "deterministico detalhe 2"],
            "missing_info_questions": [],
        },
        "policy_alignment": {
            "excluded_request": False,
            "labs_ok": "yes",
            "ecg_ok": "yes",
            "pediatric_flag": False,
            "notes": "deterministico",
        },
        "confidence": "media",
    }
    return json.dumps(payload, ensure_ascii=False)


def _extract_clinical_text(*, user_prompt: str) -> str:
    marker = "Texto clinico do relatorio:"
    if marker not in user_prompt:
        return user_prompt
    return user_prompt.split(marker, maxsplit=1)[1]


def _detect_eda_subtype(*, clinical_text: str) -> str:
    if _FOREIGN_BODY_PATTERN.search(clinical_text):
        return "foreign_body"
    if _GASTROSTOMY_PATTERN.search(clinical_text):
        return "gastrostomy"
    if _ESOPHAGEAL_DILATION_PATTERN.search(clinical_text):
        return "esophageal_dilation"
    return "standard"


def _extract_age(*, clinical_text: str) -> int:
    match = _AGE_PATTERN.search(clinical_text)
    if match is None:
        return 50
    age = int(match.group(1))
    return max(0, min(age, 130))


def _detect_asa_bucket(*, clinical_text: str) -> str:
    if _INSUFFICIENT_ASA_PATTERN.search(clinical_text):
        return "insufficient_data"
    if _HIGH_RISK_PATTERN.search(clinical_text):
        return "III ou mais"
    return "I-II"


def _detect_cardiovascular_risk(*, clinical_text: str, asa_bucket: str) -> str:
    if asa_bucket == "insufficient_data":
        return "unknown"
    if _HIGH_RISK_PATTERN.search(clinical_text):
        return "moderate_high"
    return "low"


def _canonical_procedure_name(*, subtype: str) -> str:
    if subtype == "gastrostomy":
        return "EDA para gastrostomia"
    if subtype == "esophageal_dilation":
        return "EDA para dilatacao esofagica"
    if subtype == "foreign_body":
        return "EDA para retirada de corpo estranho"
    return "EDA"


def _asa_source_hint(*, asa_bucket: str) -> str:
    if asa_bucket == "III ou mais":
        return "deterministico: contexto cardiovascular relevante"
    if asa_bucket == "insufficient_data":
        return "deterministico: dados insuficientes para ASA pratico"
    return "deterministico: baixo risco clinico"


def _cardiovascular_risk_source_hint(*, cardiovascular_risk: str) -> str:
    if cardiovascular_risk == "moderate_high":
        return "deterministico: cardiopatia ou evento cardiovascular previo"
    if cardiovascular_risk == "unknown":
        return "deterministico: risco cardiovascular nao conclusivo"
    return "deterministico: sem alto risco cardiovascular"


def _build_minimum_exam_evidence(*, subtype: str) -> dict[str, str]:
    if subtype == "foreign_body":
        return {
            "hb_or_hct_present": "unknown",
            "hb_numeric_present": "unknown",
            "platelets_numeric_present": "unknown",
            "tp_inr_rni_numeric_present": "unknown",
            "ttpa_present": "unknown",
            "urea_present": "unknown",
            "creatinine_present": "unknown",
            "coagulogram_normal_supports_ttpa": "no",
            "renal_function_preserved_supports_urea_and_creatinine": "no",
        }
    return {
        "hb_or_hct_present": "yes",
        "hb_numeric_present": "yes",
        "platelets_numeric_present": "yes",
        "tp_inr_rni_numeric_present": "yes",
        "ttpa_present": "yes",
        "urea_present": "yes",
        "creatinine_present": "yes",
        "coagulogram_normal_supports_ttpa": "no",
        "renal_function_preserved_supports_urea_and_creatinine": "no",
    }


def _build_conditional_exam_requirements(*, subtype: str) -> dict[str, str]:
    if subtype == "foreign_body":
        return {
            "ecg_required": "no",
            "chest_xray_required": "no",
            "echocardiogram_required": "no",
            "ecg_report_finding_present": "unknown",
            "chest_xray_report_finding_present": "unknown",
            "echocardiogram_report_finding_present": "unknown",
        }
    return {
        "ecg_required": "yes",
        "chest_xray_required": "no",
        "echocardiogram_required": "no",
        "ecg_report_finding_present": "yes",
        "chest_xray_report_finding_present": "yes",
        "echocardiogram_report_finding_present": "yes",
    }


def _build_clinical_flags(*, is_pediatric: bool, cardiovascular_risk: str) -> dict[str, str]:
    return {
        "hepatopathy_explicit": "no",
        "cardiopathy_explicit": "yes" if cardiovascular_risk == "moderate_high" else "no",
        "known_cardiovascular_disease": (
            "yes" if cardiovascular_risk == "moderate_high" else "no"
        ),
        "active_respiratory_symptoms": "no",
        "prior_respiratory_disease": "no",
        "multiple_comorbidities": "unknown",
        "qt_prolonging_medications": "unknown",
        "diabetes_mellitus": "unknown",
        "explicit_obesity": "unknown",
        "recent_chest_pain": "no",
        "recent_dyspnea": "no",
        "recent_palpitations": "no",
        "recent_syncope": "no",
        "unexplained_dyspnea": "unknown",
        "heart_failure_signs": "unknown",
        "new_or_unevaluated_murmur": "unknown",
        "moderate_or_severe_valvulopathy_without_recent_echo": "unknown",
        "worsening_cardiomyopathy": "unknown",
        "pulmonary_hypertension": "unknown",
        "prior_myocardial_infarction": (
            "yes" if cardiovascular_risk == "moderate_high" else "no"
        ),
        "prior_coronary_bypass": "no",
        "prior_coronary_angioplasty": (
            "yes" if cardiovascular_risk == "moderate_high" else "no"
        ),
    }


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
