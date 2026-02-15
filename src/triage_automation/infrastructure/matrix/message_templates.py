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
