"""Pydantic models for webhook callback payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    """Base model with strict unknown-field rejection."""

    model_config = ConfigDict(extra="forbid")


SupportFlag = Literal["none", "anesthesist", "anesthesist_icu"]
Decision = Literal["accept", "deny"]
AdmissionFlow = Literal["scheduled", "immediate"]


def validate_decision_support_flag(
    *,
    decision: Decision,
    support_flag: SupportFlag,
    admission_flow: AdmissionFlow | None,
) -> None:
    """Enforce decision/support/admission-flow invariants shared by decision contracts."""

    if decision == "deny" and support_flag != "none":
        raise ValueError("decision=deny requires support_flag=none")
    if decision == "deny" and admission_flow is not None:
        raise ValueError("decision=deny requires admission_flow omitted")

    if decision == "accept" and support_flag not in {
        "none",
        "anesthesist",
        "anesthesist_icu",
    }:
        raise ValueError("decision=accept requires a valid support_flag")
    if decision == "accept" and admission_flow is None:
        raise ValueError("decision=accept requires admission_flow")


class TriageDecisionWebhookPayload(StrictModel):
    """Doctor widget callback payload contract."""

    case_id: UUID
    doctor_user_id: str = Field(min_length=1)
    decision: Decision
    support_flag: SupportFlag = "none"
    admission_flow: AdmissionFlow | None = None
    reason: str | None = None
    submitted_at: datetime | None = None
    widget_event_id: str | None = None

    @model_validator(mode="after")
    def _validate_decision_specific_rules(self) -> TriageDecisionWebhookPayload:
        validate_decision_support_flag(
            decision=self.decision,
            support_flag=self.support_flag,
            admission_flow=self.admission_flow,
        )
        return self


class TriageDecisionWebhookResponse(StrictModel):
    """HTTP response model for webhook callback endpoint."""

    ok: bool
