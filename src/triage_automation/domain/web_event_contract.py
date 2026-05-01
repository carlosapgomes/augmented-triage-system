"""Contract for web-origin human events in the case timeline.

Each web event carries origin, actor, timestamp, event_type, summary_text
and case_id — the minimum fields required for auditability and timeline
rendering across all web workflow surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class WebEventOrigin(StrEnum):
    """Origin taxonomy distinguishing web events from other timeline sources."""

    WEB = "web"
    PDF = "pdf"
    LLM = "llm"
    MATRIX = "matrix"
    SYSTEM = "system"


class WebEventType(StrEnum):
    """Human web action types covering the full triage workflow lifecycle."""

    NIR_PDF_UPLOAD = "NIR_PDF_UPLOAD"
    DOCTOR_DECISION = "DOCTOR_DECISION"
    SCHEDULER_CONFIRMATION = "SCHEDULER_CONFIRMATION"
    NIR_FINAL_ACKNOWLEDGMENT = "NIR_FINAL_ACKNOWLEDGMENT"


@dataclass(frozen=True)
class WebHumanEvent:
    """Immutable contract for a single human web action in the case timeline.

    Attributes:
        case_id: The case this event belongs to.
        origin: The source channel (always ``web`` for human web actions).
        actor: The authenticated user who performed the action.
        timestamp: When the action occurred (UTC).
        event_type: The kind of human web action.
        summary_text: Human-readable textual summary for timeline rendering.
    """

    case_id: UUID
    origin: WebEventOrigin
    actor: str
    timestamp: datetime
    event_type: WebEventType
    summary_text: str
