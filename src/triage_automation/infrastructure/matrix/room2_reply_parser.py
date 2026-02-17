"""Parsing helpers for Matrix Room-2 doctor decision reply events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from triage_automation.domain.doctor_decision_parser import (
    DoctorDecisionParseError,
    parse_doctor_decision_reply,
)


@dataclass(frozen=True)
class Room2DecisionReplyEvent:
    """Normalized Room-2 doctor decision reply payload for routing."""

    room_id: str
    event_id: str
    sender_user_id: str
    reply_to_event_id: str
    case_id: UUID
    decision: str
    support_flag: str
    reason: str | None


def parse_room2_decision_reply_event(
    *,
    room_id: str,
    event: dict[str, Any],
    bot_user_id: str,
    active_root_event_id: str,
) -> Room2DecisionReplyEvent | None:
    """Parse Matrix message event into normalized Room-2 decision reply payload."""

    if not active_root_event_id:
        return None
    if event.get("type") != "m.room.message":
        return None

    sender = event.get("sender")
    if not isinstance(sender, str) or sender == bot_user_id:
        return None

    event_id = event.get("event_id")
    if not isinstance(event_id, str) or not event_id:
        return None

    content = event.get("content")
    if not isinstance(content, dict):
        return None
    if content.get("msgtype") != "m.text":
        return None

    body = content.get("body")
    if not isinstance(body, str):
        return None

    relates = content.get("m.relates_to")
    if not isinstance(relates, dict):
        return None

    reply_meta = relates.get("m.in_reply_to")
    if not isinstance(reply_meta, dict):
        return None

    reply_to_event_id = reply_meta.get("event_id")
    if not isinstance(reply_to_event_id, str) or not reply_to_event_id:
        return None
    if reply_to_event_id != active_root_event_id:
        return None

    try:
        parsed = parse_doctor_decision_reply(body=body)
    except DoctorDecisionParseError:
        return None

    return Room2DecisionReplyEvent(
        room_id=room_id,
        event_id=event_id,
        sender_user_id=sender,
        reply_to_event_id=reply_to_event_id,
        case_id=parsed.case_id,
        decision=parsed.decision,
        support_flag=parsed.support_flag,
        reason=parsed.reason,
    )
