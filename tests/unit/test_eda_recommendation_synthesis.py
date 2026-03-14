from __future__ import annotations

from triage_automation.domain.policy.eda_recommendation_synthesis import (
    synthesize_eda_support_context,
)


def _base_structured_data() -> dict[str, object]:
    return {
        "eda": {
            "asa": {
                "bucket": "I-II",
                "source_text_hint": "bom estado clinico",
            },
            "cardiovascular_risk": {
                "level": "low",
                "source_text_hint": "sem alto risco",
            },
        }
    }


def test_low_risk_asa_maps_to_no_additional_support() -> None:
    result = synthesize_eda_support_context(structured_data=_base_structured_data())

    assert result.asa_bucket == "I-II"
    assert result.asa_display == "I-II"
    assert result.support_recommendation == "none"


def test_higher_asa_maps_to_anesthesist_support() -> None:
    payload = _base_structured_data()
    eda = payload["eda"]
    assert isinstance(eda, dict)
    asa = eda["asa"]
    assert isinstance(asa, dict)
    asa["bucket"] = "III ou mais"

    result = synthesize_eda_support_context(structured_data=payload)

    assert result.asa_bucket == "III ou mais"
    assert result.asa_display == "III ou mais"
    assert result.support_recommendation == "anesthesist"


def test_moderate_high_cardiovascular_risk_maps_to_anesthesist_icu() -> None:
    payload = _base_structured_data()
    eda = payload["eda"]
    assert isinstance(eda, dict)
    cardiovascular_risk = eda["cardiovascular_risk"]
    assert isinstance(cardiovascular_risk, dict)
    cardiovascular_risk["level"] = "moderate_high"

    result = synthesize_eda_support_context(structured_data=payload)

    assert result.asa_bucket == "I-II"
    assert result.support_recommendation == "anesthesist_icu"


def test_insufficient_asa_uses_explicit_fallback_text_without_escalating_support() -> None:
    payload = _base_structured_data()
    eda = payload["eda"]
    assert isinstance(eda, dict)
    asa = eda["asa"]
    assert isinstance(asa, dict)
    asa["bucket"] = "insufficient_data"
    cardiovascular_risk = eda["cardiovascular_risk"]
    assert isinstance(cardiovascular_risk, dict)
    cardiovascular_risk["level"] = "unknown"

    result = synthesize_eda_support_context(structured_data=payload)

    assert result.asa_bucket == "insufficient_data"
    assert result.asa_display == "não foi possível estimar com os dados apresentados"
    assert result.support_recommendation == "none"
