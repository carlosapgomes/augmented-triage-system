"""Strict parser for Room-3 scheduler reply templates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

_BRT = ZoneInfo("America/Bahia")


@dataclass(frozen=True)
class SchedulerReplyParsed:
    """Normalized scheduler reply fields extracted from strict template text."""

    case_id: UUID
    appointment_status: str
    appointment_at: datetime | None
    location: str | None
    instructions: str | None
    reason: str | None


@dataclass(frozen=True)
class SchedulerParseError(ValueError):
    """Deterministic parse failure with machine-readable reason."""

    reason: str

    def __str__(self) -> str:
        return self.reason


def parse_scheduler_reply(*, body: str, expected_case_id: UUID) -> SchedulerReplyParsed:
    """Parse denied/confirmed scheduler reply template for a specific case id."""

    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not lines:
        raise SchedulerParseError("empty_message")

    case_id = _extract_case_id(lines=lines)
    if case_id != expected_case_id:
        raise SchedulerParseError("case_id_mismatch")

    first_line = lines[0].strip().lower()
    if first_line == "denied":
        reason = _extract_value(lines=lines, key="reason")
        return SchedulerReplyParsed(
            case_id=case_id,
            appointment_status="denied",
            appointment_at=None,
            location=None,
            instructions=None,
            reason=reason,
        )

    appointment_at = _parse_brt_datetime(lines[0])
    location = _extract_required_value(lines=lines, key="location")
    instructions = _extract_required_value(lines=lines, key="instructions")

    return SchedulerReplyParsed(
        case_id=case_id,
        appointment_status="confirmed",
        appointment_at=appointment_at,
        location=location,
        instructions=instructions,
        reason=None,
    )


def _extract_case_id(*, lines: list[str]) -> UUID:
    value = _extract_required_value(lines=lines, key="case")
    try:
        return UUID(value)
    except ValueError as error:
        raise SchedulerParseError("invalid_case_line") from error


def _extract_required_value(*, lines: list[str], key: str) -> str:
    value = _extract_value(lines=lines, key=key)
    if value is None or not value:
        if key == "case":
            raise SchedulerParseError("missing_case_line")
        raise SchedulerParseError(f"missing_{key}_line")
    return value


def _extract_value(*, lines: list[str], key: str) -> str | None:
    prefix = f"{key.lower()}:"
    for line in lines:
        normalized = line.lower()
        if normalized.startswith(prefix):
            return line[len(prefix) :].strip()
    return None


def _parse_brt_datetime(line: str) -> datetime:
    expected_suffix = " BRT"
    if not line.endswith(expected_suffix):
        raise SchedulerParseError("invalid_confirmed_datetime")

    raw = line[: -len(expected_suffix)]
    try:
        naive = datetime.strptime(raw, "%d-%m-%Y %H:%M")
    except ValueError as error:
        raise SchedulerParseError("invalid_confirmed_datetime") from error

    return naive.replace(tzinfo=_BRT)
