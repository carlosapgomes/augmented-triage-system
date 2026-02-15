"""Matrix message templates for triage workflow posts."""

from __future__ import annotations

import json
from uuid import UUID


def build_room2_widget_message(
    *,
    case_id: UUID,
    agency_record_number: str,
    payload: dict[str, object],
) -> str:
    """Build Room-2 widget post body with embedded JSON payload."""

    payload_json = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    return (
        "Triage request\n"
        f"case: {case_id}\n"
        f"record: {agency_record_number}\n\n"
        "Widget payload:\n"
        f"```json\n{payload_json}\n```"
    )


def build_room2_ack_message(*, case_id: UUID) -> str:
    """Build Room-2 ack body used as audit-only reaction target."""

    return f"Triage recorded for case: {case_id}\nReact +1 to acknowledge."


def build_room3_request_message(*, case_id: UUID) -> str:
    """Build Room-3 scheduling request body including strict reply instructions."""

    return (
        "Scheduling request\n"
        "Reply using one of the strict formats below.\n\n"
        "Confirmed:\n"
        "DD-MM-YYYY HH:MM BRT\n"
        "location: <free text>\n"
        "instructions: <free text>\n"
        f"case: {case_id}\n\n"
        "Denied:\n"
        "denied\n"
        "reason: <optional free text>\n"
        f"case: {case_id}"
    )


def build_room3_ack_message(*, case_id: UUID) -> str:
    """Build Room-3 ack body used as audit-only reaction target."""

    return f"Scheduling request recorded for case: {case_id}\nReact +1 to acknowledge."


def build_room3_invalid_format_reprompt(*, case_id: UUID) -> str:
    """Build strict Room-3 reformat prompt for invalid scheduler replies."""

    return (
        "I could not parse your response for this case.\n\n"
        "Please reply using ONE of the formats below (one field per line) and include the "
        "case line.\n\n"
        "CONFIRMED:\n"
        "DD-MM-YYYY HH:MM BRT\n"
        "location: ...\n"
        "instructions: ...\n"
        f"case: {case_id}\n\n"
        "DENIED:\n"
        "denied\n"
        "reason: ...\n"
        f"case: {case_id}"
    )
