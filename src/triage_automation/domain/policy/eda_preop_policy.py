"""Deterministic pre-procedure EDA policy evaluation rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

DecisionValue = Literal["accept", "deny", "excluded", "manual_review_required"]

_OPERATIONAL_INDICATIONS = {"bleeding", "abdominal_pain", "dyspepsia"}


@dataclass(frozen=True)
class EdaPreopDecision:
    """Deterministic pre-procedure decision with explicit reason metadata."""

    decision: DecisionValue
    reason_code: str
    reason_text: str
    evidence_spans: list[dict[str, str]]
    pediatric_flag: bool

    def to_dict(self) -> dict[str, object]:
        """Serialize deterministic decision payload for persistence and downstream use."""

        return {
            "decision": self.decision,
            "reason_code": self.reason_code,
            "reason_text": self.reason_text,
            "evidence_spans": self.evidence_spans,
            "pediatric_flag": self.pediatric_flag,
        }


def evaluate_eda_preop_policy(*, structured_data: dict[str, object]) -> dict[str, object]:
    """Evaluate deterministic EDA pre-procedure criteria from structured extraction."""

    eda_payload = _extract_dict(structured_data, "eda")
    preop_payload = _extract_dict(structured_data, "preop_screening")

    exclusion_type = _extract_text(eda_payload, "exclusion_type")
    if exclusion_type == "gastrostomy":
        return EdaPreopDecision(
            decision="excluded",
            reason_code="excluded_gastrostomy",
            reason_text="Solicitação de gastrostomia fora de escopo da política automática EDA.",
            evidence_spans=_extract_evidence_spans(preop_payload),
            pediatric_flag=_is_pediatric(structured_data),
        ).to_dict()

    if exclusion_type == "esophageal_dilation":
        return EdaPreopDecision(
            decision="excluded",
            reason_code="excluded_esophageal_dilation",
            reason_text=(
                "Solicitação de dilatação esofágica fora de escopo da política automática EDA."
            ),
            evidence_spans=_extract_evidence_spans(preop_payload),
            pediatric_flag=_is_pediatric(structured_data),
        ).to_dict()

    has_cardiovascular_disease = _extract_text(preop_payload, "has_cardiovascular_disease")
    has_ecg_report = _extract_text(preop_payload, "has_ecg_report")
    if has_cardiovascular_disease == "yes" and has_ecg_report != "yes":
        return _deny(
            reason_code="missing_ecg_with_cardiovascular_disease",
            reason_text=(
                "Risco cardiovascular relatado sem laudo de ECG obrigatório para "
                "recomendação automática EDA."
            ),
            structured_data=structured_data,
        )

    indication_category = _extract_text(eda_payload, "indication_category")
    if indication_category == "foreign_body":
        return EdaPreopDecision(
            decision="accept",
            reason_code="foreign_body_exception",
            reason_text="Exceção de corpo estranho: sem gate laboratorial de rotina nesta etapa.",
            evidence_spans=_extract_evidence_spans(preop_payload),
            pediatric_flag=_is_pediatric(structured_data),
        ).to_dict()

    if indication_category in _OPERATIONAL_INDICATIONS:
        hb = _extract_float(preop_payload, "hb_g_dl")
        if hb is not None and hb <= 7:
            return _deny(
                reason_code="hb_below_threshold",
                reason_text="HB <= 7 para cenário operacional (hemorragia/dor/dispepsia).",
                structured_data=structured_data,
            )

        platelets = _extract_int(preop_payload, "platelets_per_mm3")
        if platelets is not None and platelets <= 100000:
            return _deny(
                reason_code="platelets_below_threshold",
                reason_text=(
                    "Plaquetas <= 100000 para cenário operacional "
                    "(hemorragia/dor/dispepsia)."
                ),
                structured_data=structured_data,
            )

        inr = _extract_float(preop_payload, "inr")
        if inr is not None and inr >= 1.5:
            return _deny(
                reason_code="inr_above_threshold",
                reason_text="INR >= 1.5 para cenário operacional (hemorragia/dor/dispepsia).",
                structured_data=structured_data,
            )

        has_ecg_report = _extract_text(preop_payload, "has_ecg_report")
        if has_ecg_report != "yes":
            return _deny(
                reason_code="missing_ecg_with_cardiovascular_disease",
                reason_text="ECG obrigatório ausente para cenário operacional.",
                structured_data=structured_data,
            )
    else:
        hb = _extract_float(preop_payload, "hb_g_dl")
        if hb is not None and hb < 7:
            return _deny(
                reason_code="hb_below_threshold",
                reason_text="HB < 7 para baseline CHD em demais indicações EDA.",
                structured_data=structured_data,
            )

        platelets = _extract_int(preop_payload, "platelets_per_mm3")
        if platelets is not None and platelets < 50000:
            return _deny(
                reason_code="platelets_below_threshold",
                reason_text=(
                    "Plaquetas < 50000 para baseline CHD em demais indicações EDA."
                ),
                structured_data=structured_data,
            )

        inr = _extract_float(preop_payload, "inr")
        if inr is not None and inr > 2:
            return _deny(
                reason_code="inr_above_threshold",
                reason_text="INR > 2 para baseline CHD em demais indicações EDA.",
                structured_data=structured_data,
            )

    return EdaPreopDecision(
        decision="accept",
        reason_code="criteria_met",
        reason_text="Critérios determinísticos avaliados sem gatilhos de negação nesta etapa.",
        evidence_spans=_extract_evidence_spans(preop_payload),
        pediatric_flag=_is_pediatric(structured_data),
    ).to_dict()


def _deny(
    *,
    reason_code: str,
    reason_text: str,
    structured_data: dict[str, object],
) -> dict[str, object]:
    preop_payload = _extract_dict(structured_data, "preop_screening")
    return EdaPreopDecision(
        decision="deny",
        reason_code=reason_code,
        reason_text=reason_text,
        evidence_spans=_extract_evidence_spans(preop_payload),
        pediatric_flag=_is_pediatric(structured_data),
    ).to_dict()


def _extract_dict(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload.get(key)
    if isinstance(value, dict):
        return value
    return {}


def _extract_text(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized


def _extract_float(payload: dict[str, object], key: str) -> float | None:
    value = payload.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _extract_int(payload: dict[str, object], key: str) -> int | None:
    value = payload.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _extract_evidence_spans(preop_payload: dict[str, object]) -> list[dict[str, str]]:
    raw = preop_payload.get("evidence_spans")
    if not isinstance(raw, list):
        return []

    spans: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        field_path = item.get("field_path")
        excerpt = item.get("excerpt")
        if not isinstance(field_path, str) or not isinstance(excerpt, str):
            continue
        normalized_path = field_path.strip()
        normalized_excerpt = excerpt.strip()
        if not normalized_path or not normalized_excerpt:
            continue
        spans.append({"field_path": normalized_path, "excerpt": normalized_excerpt})
    return spans


def _is_pediatric(structured_data: dict[str, object]) -> bool:
    patient_payload = _extract_dict(structured_data, "patient")
    age = patient_payload.get("age")
    if isinstance(age, bool):
        return False
    if isinstance(age, int):
        return age < 16
    return False
