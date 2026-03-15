"""Patient context extraction helpers shared by Room-3 and Room-1 messaging."""

from __future__ import annotations

from typing import Any

_SUPPORTED_EDA_SUBTYPES = {
    "standard",
    "gastrostomy",
    "esophageal_dilation",
    "foreign_body",
}


def extract_patient_name_age(
    structured_data_json: dict[str, Any] | None,
) -> tuple[str | None, str | None]:
    """Extract patient name and age from LLM1 structured payload."""

    if not isinstance(structured_data_json, dict):
        return None, None

    patient_raw = structured_data_json.get("patient")
    if not isinstance(patient_raw, dict):
        patient_raw = structured_data_json.get("paciente")
    if not isinstance(patient_raw, dict):
        return None, None

    patient_name = _normalize_optional_string(patient_raw.get("name"))
    if patient_name is None:
        patient_name = _normalize_optional_string(patient_raw.get("nome"))

    patient_age = _normalize_age(patient_raw.get("age"))
    if patient_age is None:
        patient_age = _normalize_age(patient_raw.get("idade"))

    return patient_name, patient_age



def extract_requested_exam(structured_data_json: dict[str, Any] | None) -> str | None:
    """Extract requested exam/procedure name from LLM1 structured payload."""

    requested_raw = _extract_requested_procedure_payload(structured_data_json)
    if requested_raw is None:
        return None

    exam_name = _normalize_optional_string(requested_raw.get("name"))
    if exam_name is None:
        exam_name = _normalize_optional_string(requested_raw.get("nome"))
    return exam_name



def extract_supported_eda_subtype(structured_data_json: dict[str, Any] | None) -> str | None:
    """Extract normalized supported EDA subtype from structured payload."""

    requested_raw = _extract_requested_procedure_payload(structured_data_json)
    if requested_raw is not None:
        subtype = _normalize_optional_string(requested_raw.get("subtype"))
        if subtype in _SUPPORTED_EDA_SUBTYPES:
            return subtype
        return "standard"

    if not isinstance(structured_data_json, dict):
        return None

    preop_screening = structured_data_json.get("preop_screening")
    if not isinstance(preop_screening, dict):
        return None

    rulebook_signals = preop_screening.get("rulebook_signals")
    if not isinstance(rulebook_signals, dict):
        return None

    rulebook_subtype = _normalize_optional_string(rulebook_signals.get("eda_subtype"))
    if rulebook_subtype in _SUPPORTED_EDA_SUBTYPES:
        return rulebook_subtype
    return None



def extract_pediatric_flag(structured_data_json: dict[str, Any] | None) -> bool | None:
    """Extract deterministic pediatric marker from the structured payload."""

    if not isinstance(structured_data_json, dict):
        return None

    patient_raw = structured_data_json.get("patient")
    if not isinstance(patient_raw, dict):
        patient_raw = structured_data_json.get("paciente")
    if isinstance(patient_raw, dict):
        patient_age = _coerce_age_number(patient_raw.get("age"))
        if patient_age is None:
            patient_age = _coerce_age_number(patient_raw.get("idade"))
        if patient_age is not None:
            return patient_age < 16

    eda_raw = structured_data_json.get("eda")
    if isinstance(eda_raw, dict):
        eda_is_pediatric = eda_raw.get("is_pediatric")
        if isinstance(eda_is_pediatric, bool):
            return eda_is_pediatric

    policy_precheck = structured_data_json.get("policy_precheck")
    if isinstance(policy_precheck, dict):
        pediatric_flag = policy_precheck.get("pediatric_flag")
        if isinstance(pediatric_flag, bool):
            return pediatric_flag

    return None



def _extract_requested_procedure_payload(
    structured_data_json: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(structured_data_json, dict):
        return None

    eda_raw = structured_data_json.get("eda")
    if not isinstance(eda_raw, dict):
        return None

    requested_raw = eda_raw.get("requested_procedure")
    if not isinstance(requested_raw, dict):
        requested_raw = eda_raw.get("procedimento_solicitado")
    if not isinstance(requested_raw, dict):
        return None
    return requested_raw



def _normalize_optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized



def _normalize_age(value: object) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(value)
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        return normalized
    return str(value)



def _coerce_age_number(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        return None
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized or not normalized.isdigit():
            return None
        return int(normalized)
    return None
