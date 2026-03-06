from __future__ import annotations

import importlib
from typing import cast

import pytest


def _base_llm1_structured_data() -> dict[str, object]:
    return {
        "schema_version": "1.1",
        "language": "pt-BR",
        "agency_record_number": "12345",
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
            "requested_procedure": {"name": "EDA", "urgency": "eletivo"},
            "labs": {
                "hb_g_dl": 10.5,
                "platelets_per_mm3": 180000,
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
            "hb_g_dl": 10.5,
            "platelets_per_mm3": 180000,
            "inr": 1.1,
            "evidence_spans": [],
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
            "bullet_points": ["a", "b", "c"],
        },
        "extraction_quality": {
            "confidence": "media",
            "missing_fields": [],
            "notes": None,
        },
    }


def _evaluate_preop_policy(*, structured_data: dict[str, object]) -> dict[str, object]:
    module = importlib.import_module("triage_automation.domain.policy.eda_preop_policy")
    evaluate = getattr(module, "evaluate_eda_preop_policy")
    result = evaluate(structured_data=structured_data)
    assert isinstance(result, dict)
    return cast(dict[str, object], result)


@pytest.mark.parametrize(
    ("exclusion_type", "reason_code"),
    [
        ("gastrostomy", "excluded_gastrostomy"),
        ("esophageal_dilation", "excluded_esophageal_dilation"),
    ],
)
def test_exclusions_take_priority_over_threshold_denials(
    exclusion_type: str,
    reason_code: str,
) -> None:
    payload = _base_llm1_structured_data()
    eda = cast(dict[str, object], payload["eda"])
    eda["exclusion_type"] = exclusion_type

    preop = cast(dict[str, object], payload["preop_screening"])
    preop["hb_g_dl"] = 5.0
    preop["platelets_per_mm3"] = 30000
    preop["inr"] = 3.0
    preop["has_ecg_report"] = "no"

    result = _evaluate_preop_policy(structured_data=payload)

    assert result["decision"] == "excluded"
    assert result["reason_code"] == reason_code


def test_foreign_body_exception_does_not_trigger_routine_labs_denial() -> None:
    payload = _base_llm1_structured_data()
    eda = cast(dict[str, object], payload["eda"])
    eda["indication_category"] = "foreign_body"

    preop = cast(dict[str, object], payload["preop_screening"])
    preop["hb_g_dl"] = None
    preop["platelets_per_mm3"] = None
    preop["inr"] = None

    result = _evaluate_preop_policy(structured_data=payload)

    assert result["decision"] != "deny"
    assert result.get("reason_code") not in {
        "hb_below_threshold",
        "platelets_below_threshold",
        "inr_above_threshold",
    }


@pytest.mark.parametrize("indication", ["bleeding", "abdominal_pain", "dyspepsia"])
def test_operational_indications_deny_hb_equal_to_7(indication: str) -> None:
    payload = _base_llm1_structured_data()
    eda = cast(dict[str, object], payload["eda"])
    eda["indication_category"] = indication

    preop = cast(dict[str, object], payload["preop_screening"])
    preop["hb_g_dl"] = 7.0
    preop["platelets_per_mm3"] = 150000
    preop["inr"] = 1.1
    preop["has_ecg_report"] = "yes"

    result = _evaluate_preop_policy(structured_data=payload)

    assert result["decision"] == "deny"
    assert result["reason_code"] == "hb_below_threshold"


def test_operational_indications_require_ecg_report() -> None:
    payload = _base_llm1_structured_data()
    eda = cast(dict[str, object], payload["eda"])
    eda["indication_category"] = "dyspepsia"

    preop = cast(dict[str, object], payload["preop_screening"])
    preop["hb_g_dl"] = 10.5
    preop["platelets_per_mm3"] = 180000
    preop["inr"] = 1.1
    preop["has_ecg_report"] = "no"

    result = _evaluate_preop_policy(structured_data=payload)

    assert result["decision"] == "deny"


def test_operational_indications_deny_platelets_equal_to_100k() -> None:
    payload = _base_llm1_structured_data()
    eda = cast(dict[str, object], payload["eda"])
    eda["indication_category"] = "abdominal_pain"

    preop = cast(dict[str, object], payload["preop_screening"])
    preop["hb_g_dl"] = 10.5
    preop["platelets_per_mm3"] = 100000
    preop["inr"] = 1.1
    preop["has_ecg_report"] = "yes"

    result = _evaluate_preop_policy(structured_data=payload)

    assert result["decision"] == "deny"
    assert result["reason_code"] == "platelets_below_threshold"


def test_operational_indications_deny_inr_equal_to_1_5() -> None:
    payload = _base_llm1_structured_data()
    eda = cast(dict[str, object], payload["eda"])
    eda["indication_category"] = "bleeding"

    preop = cast(dict[str, object], payload["preop_screening"])
    preop["hb_g_dl"] = 10.5
    preop["platelets_per_mm3"] = 150000
    preop["inr"] = 1.5
    preop["has_ecg_report"] = "yes"

    result = _evaluate_preop_policy(structured_data=payload)

    assert result["decision"] == "deny"
    assert result["reason_code"] == "inr_above_threshold"


def test_baseline_non_operational_eda_deny_hb_below_7() -> None:
    payload = _base_llm1_structured_data()
    eda = cast(dict[str, object], payload["eda"])
    eda["indication_category"] = "other"

    preop = cast(dict[str, object], payload["preop_screening"])
    preop["hb_g_dl"] = 6.9
    preop["platelets_per_mm3"] = 180000
    preop["inr"] = 1.1

    result = _evaluate_preop_policy(structured_data=payload)

    assert result["decision"] == "deny"
    assert result["reason_code"] == "hb_below_threshold"


def test_baseline_non_operational_eda_deny_platelets_below_50k() -> None:
    payload = _base_llm1_structured_data()
    eda = cast(dict[str, object], payload["eda"])
    eda["indication_category"] = "other"

    preop = cast(dict[str, object], payload["preop_screening"])
    preop["hb_g_dl"] = 10.5
    preop["platelets_per_mm3"] = 49999
    preop["inr"] = 1.1

    result = _evaluate_preop_policy(structured_data=payload)

    assert result["decision"] == "deny"
    assert result["reason_code"] == "platelets_below_threshold"


def test_baseline_non_operational_eda_deny_inr_above_2() -> None:
    payload = _base_llm1_structured_data()
    eda = cast(dict[str, object], payload["eda"])
    eda["indication_category"] = "other"

    preop = cast(dict[str, object], payload["preop_screening"])
    preop["hb_g_dl"] = 10.5
    preop["platelets_per_mm3"] = 180000
    preop["inr"] = 2.1

    result = _evaluate_preop_policy(structured_data=payload)

    assert result["decision"] == "deny"
    assert result["reason_code"] == "inr_above_threshold"


def test_all_eda_deny_when_cardiovascular_risk_and_missing_ecg() -> None:
    payload = _base_llm1_structured_data()
    eda = cast(dict[str, object], payload["eda"])
    eda["indication_category"] = "other"

    preop = cast(dict[str, object], payload["preop_screening"])
    preop["has_cardiovascular_disease"] = "yes"
    preop["has_ecg_report"] = "no"
    preop["hb_g_dl"] = 10.5
    preop["platelets_per_mm3"] = 180000
    preop["inr"] = 1.1

    result = _evaluate_preop_policy(structured_data=payload)

    assert result["decision"] == "deny"
    assert result["reason_code"] == "missing_ecg_with_cardiovascular_disease"


@pytest.mark.parametrize(
    "risk_field",
    ["has_active_respiratory_symptoms", "has_prior_respiratory_disease"],
)
def test_all_eda_deny_when_respiratory_risk_and_missing_chest_xray(
    risk_field: str,
) -> None:
    payload = _base_llm1_structured_data()
    eda = cast(dict[str, object], payload["eda"])
    eda["indication_category"] = "other"

    preop = cast(dict[str, object], payload["preop_screening"])
    preop[risk_field] = "yes"
    preop["has_chest_xray_report"] = "no"
    preop["has_ecg_report"] = "yes"
    preop["hb_g_dl"] = 10.5
    preop["platelets_per_mm3"] = 180000
    preop["inr"] = 1.1

    result = _evaluate_preop_policy(structured_data=payload)

    assert result["decision"] == "deny"
    assert result["reason_code"] == "missing_chest_xray_with_respiratory_risk"
