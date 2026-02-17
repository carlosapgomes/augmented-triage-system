"""Strict parser for Room-3 scheduler reply templates."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

_BRT = ZoneInfo("America/Bahia")
_KEY_ALIASES: dict[str, tuple[str, ...]] = {
    "case": ("case", "caso"),
    "status": ("status", "situacao", "situação", "estado"),
    "date_time": (
        "data_hora",
        "datahora",
        "datetime",
        "data_hora_brt",
        "data_hora_local",
        "data/hora",
    ),
    "location": ("location", "local"),
    "instructions": ("instructions", "instrucoes", "instruções"),
    "reason": ("reason", "motivo"),
}
_EMPTY_REASON_MARKERS = {
    "",
    "(opcional)",
    "opcional",
    "(vazio)",
    "vazio",
    "-",
    "n/a",
    "na",
}
_UUID_PATTERN = re.compile(
    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
)


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

    lines = _normalized_message_lines(body=body)
    if not lines:
        raise SchedulerParseError("empty_message")

    if _extract_value(lines=lines, key="status") is not None:
        return _parse_status_template(lines=lines, expected_case_id=expected_case_id)

    case_id = _extract_case_id(lines=lines)
    if case_id != expected_case_id:
        raise SchedulerParseError("case_id_mismatch")

    parsed_lines = _strip_section_headers(lines)
    if not parsed_lines:
        raise SchedulerParseError("empty_message")

    first_line = parsed_lines[0].strip().lower()
    if first_line in {"denied", "negado"}:
        reason = _extract_value(lines=parsed_lines, key="reason")
        return SchedulerReplyParsed(
            case_id=case_id,
            appointment_status="denied",
            appointment_at=None,
            location=None,
            instructions=None,
            reason=reason,
        )

    appointment_at = _parse_brt_datetime(parsed_lines[0])
    location = _extract_required_value(lines=parsed_lines, key="location")
    instructions = _extract_required_value(lines=parsed_lines, key="instructions")

    return SchedulerReplyParsed(
        case_id=case_id,
        appointment_status="confirmed",
        appointment_at=appointment_at,
        location=location,
        instructions=instructions,
        reason=None,
    )


def _parse_status_template(
    *,
    lines: list[str],
    expected_case_id: UUID,
) -> SchedulerReplyParsed:
    case_id = _extract_case_id(lines=lines)
    if case_id != expected_case_id:
        raise SchedulerParseError("case_id_mismatch")

    status_raw = _extract_required_value(lines=lines, key="status").strip().lower()
    if status_raw in {"confirmado", "confirmed"}:
        date_time_raw = _extract_required_value(lines=lines, key="date_time")
        appointment_at = _parse_brt_datetime(date_time_raw)
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

    if status_raw in {"negado", "denied"}:
        reason_raw = _extract_value(lines=lines, key="reason")
        reason = _normalize_reason(reason_raw)
        return SchedulerReplyParsed(
            case_id=case_id,
            appointment_status="denied",
            appointment_at=None,
            location=None,
            instructions=None,
            reason=reason,
        )

    raise SchedulerParseError("invalid_status_value")


def _extract_case_id(*, lines: list[str]) -> UUID:
    value = _extract_required_value(lines=lines, key="case")
    match = _UUID_PATTERN.search(value)
    if match is not None:
        value = match.group(1)
    try:
        return UUID(value)
    except ValueError as error:
        raise SchedulerParseError("invalid_case_line") from error


def _strip_section_headers(lines: list[str]) -> list[str]:
    """Normalize optional section header lines used in Room-3 templates."""

    if not lines:
        return lines

    first_line = lines[0].strip().lower()
    if first_line in {"confirmed", "confirmed:", "confirmado", "confirmado:"}:
        return lines[1:]
    if first_line in {"denied:", "negado:"}:
        if len(lines) >= 2 and lines[1].strip().lower() in {"denied", "negado"}:
            return lines[1:]
        return ["denied", *lines[1:]]

    return lines


def _extract_required_value(*, lines: list[str], key: str) -> str:
    value = _extract_value(lines=lines, key=key)
    if value is None or not value:
        if key == "case":
            raise SchedulerParseError("missing_case_line")
        raise SchedulerParseError(f"missing_{key}_line")
    return value


def _extract_value(*, lines: list[str], key: str) -> str | None:
    aliases = {_normalize_key(alias) for alias in _KEY_ALIASES.get(key, (key,))}
    value: str | None = None
    for line_key, line_value in _iter_labeled_values(lines=lines):
        if line_key not in aliases:
            continue
        if line_value:
            value = line_value
            continue
        if value is None:
            value = ""
    return value


def _iter_labeled_values(*, lines: list[str]) -> list[tuple[str, str]]:
    labeled: list[tuple[str, str]] = []
    for raw_line in lines:
        normalized_line = raw_line.replace("：", ":")
        if ":" not in normalized_line:
            continue
        raw_key, raw_value = normalized_line.split(":", 1)
        key = _normalize_key(raw_key)
        if not key:
            continue
        labeled.append((key, raw_value.strip()))
    return labeled


def _normalized_message_lines(*, body: str) -> list[str]:
    lines: list[str] = []
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("```"):
            continue
        if line.startswith(">"):
            continue
        lines.append(line)
    return lines


def _normalize_reason(reason: str | None) -> str | None:
    if reason is None:
        return None
    normalized = reason.strip()
    if normalized.lower() in _EMPTY_REASON_MARKERS:
        return None
    return normalized


def _parse_brt_datetime(line: str) -> datetime:
    value = line.strip().replace("：", ":")
    value = re.sub(r"\s+", " ", value).strip("`")
    value = re.sub(r"\s*brt\.?\s*$", "", value, flags=re.IGNORECASE)

    formats = ("%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M")
    for date_format in formats:
        try:
            naive = datetime.strptime(value, date_format)
            return naive.replace(tzinfo=_BRT)
        except ValueError:
            continue

    raise SchedulerParseError("invalid_confirmed_datetime")


def _normalize_key(raw_key: str) -> str:
    key = raw_key.strip().lower()
    key = key.strip("`*_ ")
    key = re.sub(r"^[>\-–—*•\d\.\)\( ]+", "", key)
    key = key.replace("-", "_").replace("/", "_").replace(" ", "_")
    key = _strip_diacritics(key)
    key = re.sub(r"_+", "_", key)
    return key.strip("_")


def _strip_diacritics(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(character for character in decomposed if not unicodedata.combining(character))
