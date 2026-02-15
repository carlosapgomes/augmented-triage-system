"""Pydantic schema models for LLM1 structured extraction response v1.1."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Base model with strict unknown-field rejection."""

    model_config = ConfigDict(extra="forbid")


class Llm1Patient(StrictModel):
    """Patient identity and demographic fields extracted by LLM1."""

    name: str | None
    age: int | None = Field(default=None, ge=0, le=130)
    sex: Literal["M", "F", "Outro"] | None
    document_id: str | None = None


class Llm1RequestedProcedure(StrictModel):
    """Requested procedure metadata and urgency."""

    name: str | None
    urgency: Literal["eletivo", "urgente", "emergente", "indefinido"]


class Llm1Labs(StrictModel):
    """Laboratory values and provenance hints."""

    hb_g_dl: float | None
    platelets_per_mm3: int | None
    inr: float | None
    source_text_hint: str | None


class Llm1Ecg(StrictModel):
    """ECG availability and abnormality signal."""

    report_present: Literal["yes", "no", "unknown"]
    abnormal_flag: Literal["yes", "no", "unknown"]
    source_text_hint: str | None


class Llm1Asa(StrictModel):
    """ASA class estimate and confidence."""

    class_: Literal["I", "II", "III", "IV", "V", "unknown"] = Field(alias="class")
    confidence: Literal["alta", "media", "baixa"]
    rationale: str | None


class Llm1CardiovascularRisk(StrictModel):
    """Cardiovascular risk assessment and confidence."""

    level: Literal["low", "moderate", "high", "unknown"]
    confidence: Literal["alta", "media", "baixa"]
    rationale: str | None


class Llm1Eda(StrictModel):
    """EDA-focused structured clinical extraction fields."""

    indication_category: Literal[
        "foreign_body",
        "bleeding",
        "abdominal_pain",
        "dyspepsia",
        "other",
        "unknown",
    ]
    exclusion_type: Literal["none", "gastrostomy", "esophageal_dilation", "unknown"]
    is_pediatric: bool
    foreign_body_suspected: bool
    requested_procedure: Llm1RequestedProcedure
    labs: Llm1Labs
    ecg: Llm1Ecg
    asa: Llm1Asa
    cardiovascular_risk: Llm1CardiovascularRisk


class Llm1PolicyPrecheck(StrictModel):
    """Precheck flags used by deterministic policy reconciliation."""

    excluded_from_eda_flow: bool
    exclusion_reason: str | None
    labs_required: bool
    labs_pass: Literal["yes", "no", "unknown"]
    labs_failed_items: list[str]
    ecg_required: bool
    ecg_present: Literal["yes", "no", "unknown"]
    pediatric_flag: bool
    notes: str | None


class Llm1Summary(StrictModel):
    """Human-readable one-liner and supporting bullets."""

    one_liner: str
    bullet_points: list[str] = Field(min_length=3, max_length=8)


class Llm1ExtractionQuality(StrictModel):
    """Quality/confidence metadata for extraction completeness."""

    confidence: Literal["alta", "media", "baixa"]
    missing_fields: list[str]
    notes: str | None


class Llm1Response(StrictModel):
    """Top-level LLM1 response schema v1.1."""

    schema_version: Literal["1.1"]
    language: Literal["pt-BR"]
    agency_record_number: str = Field(pattern=r"^[0-9]{5}$")
    patient: Llm1Patient
    eda: Llm1Eda
    policy_precheck: Llm1PolicyPrecheck
    summary: Llm1Summary
    extraction_quality: Llm1ExtractionQuality
