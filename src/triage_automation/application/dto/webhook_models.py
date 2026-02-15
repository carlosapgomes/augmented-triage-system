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


class TriageDecisionWebhookPayload(StrictModel):
    """Doctor widget callback payload contract."""

    case_id: UUID
    doctor_user_id: str = Field(min_length=1)
    decision: Decision
    support_flag: SupportFlag = "none"
    reason: str | None = None
    submitted_at: datetime | None = None
    widget_event_id: str | None = None

    @model_validator(mode="after")
    def _validate_decision_specific_rules(self) -> TriageDecisionWebhookPayload:
        if self.decision == "deny" and self.support_flag != "none":
            raise ValueError("decision=deny requires support_flag=none")

        if self.decision == "accept" and self.support_flag not in {
            "none",
            "anesthesist",
            "anesthesist_icu",
        }:
            raise ValueError("decision=accept requires a valid support_flag")

        return self


class TriageDecisionWebhookResponse(StrictModel):
    """HTTP response model for webhook callback endpoint."""

    ok: bool
