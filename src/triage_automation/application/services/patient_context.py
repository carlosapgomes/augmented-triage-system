"""Patient context extraction helpers shared by Room-3 and Room-1 messaging."""

from __future__ import annotations

from typing import Any


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
