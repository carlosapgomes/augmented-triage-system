"""Service for handling Room-2 doctor decision replies."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from triage_automation.application.dto.webhook_models import (
    Decision,
    SupportFlag,
    TriageDecisionWebhookPayload,
)
from triage_automation.application.services.handle_doctor_decision_service import (
    HandleDoctorDecisionOutcome,
    HandleDoctorDecisionService,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Room2ReplyEvent:
    """Normalized Room-2 doctor decision reply payload for handling."""

    room_id: str
    event_id: str
    sender_user_id: str
    reply_to_event_id: str
    case_id: UUID
    decision: Decision
    support_flag: SupportFlag
    reason: str | None


@dataclass(frozen=True)
class Room2ReplyResult:
    """Outcome model for Room-2 reply handling."""

    processed: bool
    reason: str | None = None


class Room2ReplyService:
    """Route parsed Room-2 reply payloads into existing doctor decision service."""

    def __init__(
        self,
        *,
        room2_id: str,
        decision_service: HandleDoctorDecisionService,
    ) -> None:
        self._room2_id = room2_id
        self._decision_service = decision_service

    async def handle_reply(self, event: Room2ReplyEvent) -> Room2ReplyResult:
        """Handle Room-2 parsed decision reply through existing decision path."""

        if event.room_id != self._room2_id:
            return Room2ReplyResult(processed=False, reason="wrong_room")

        # Matrix sender identity is authoritative for doctor attribution in Room-2.
        doctor_user_id = event.sender_user_id
        payload = TriageDecisionWebhookPayload(
            case_id=event.case_id,
            doctor_user_id=doctor_user_id,
            decision=event.decision,
            support_flag=event.support_flag,
            reason=event.reason,
            widget_event_id=event.event_id,
        )
        result = await self._decision_service.handle(payload)
        if result.outcome is HandleDoctorDecisionOutcome.APPLIED:
            logger.info(
                "room2_reply_applied case_id=%s doctor_user_id=%s",
                event.case_id,
                doctor_user_id,
            )
            return Room2ReplyResult(processed=True)

        return Room2ReplyResult(processed=False, reason=result.outcome.value)
