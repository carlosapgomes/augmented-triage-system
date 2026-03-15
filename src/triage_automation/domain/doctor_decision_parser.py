"""Strict parser for Room-2 doctor decision reply templates."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from uuid import UUID

_REQUIRED_KEYS = ("decision", "case_id")
_ACCEPT_REQUIRED_KEYS = ("support_flag", "admission_flow")
_KEY_ALIASES: dict[str, tuple[str, ...]] = {
    "decision": ("decision", "decisao", "decisão"),
    "support_flag": ("support_flag", "suporte"),
    "admission_flow": (
        "admission_flow",
        "admission flow",
        "fluxo de admissao",
        "fluxo de admissão",
        "fluxo_admissao",
    ),
    "reason": ("reason", "motivo"),
    "case_id": ("case_id", "caso"),
}
_FORBIDDEN_TYPED_IDENTITY_KEYS = {
    "doctor_user_id",
    "medico_user_id",
    "usuario_medico",
}
_DECISION_ALIASES: dict[str, str] = {
    "accept": "accept",
    "deny": "deny",
    "aceitar": "accept",
    "aceito": "accept",
    "aceita": "accept",
    "negar": "deny",
    "negado": "deny",
    "negar.": "deny",
}
_SUPPORT_ALIASES: dict[str, str] = {
    "none": "none",
    "nenhum": "none",
    "anesthesist": "anesthesist",
    "anestesista": "anesthesist",
    "anesthesist_icu": "anesthesist_icu",
    "anestesista_uti": "anesthesist_icu",
    "anestesista_icu": "anesthesist_icu",
}
_ADMISSION_FLOW_ALIASES: dict[str, str] = {
    "scheduled": "scheduled",
    "agendamento": "scheduled",
    "immediate": "immediate",
    "vinda_imediata": "immediate",
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
class DoctorDecisionReplyParsed:
    """Normalized doctor decision fields extracted from strict template text."""

    case_id: UUID
    decision: str
    support_flag: str
    admission_flow: str | None
    reason: str | None


class DoctorDecisionParseError(ValueError):
    """Deterministic parse failure with machine-readable reason."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason

    def __str__(self) -> str:
        return self.reason


def parse_doctor_decision_reply(
    *,
    body: str,
    expected_case_id: UUID | None = None,
) -> DoctorDecisionReplyParsed:
    """Parse strict Room-2 doctor decision reply template."""

    lines = _normalized_message_lines(body=body)
    if not lines:
        raise DoctorDecisionParseError("empty_message")

    parsed_fields: dict[str, str] = {}
    for line in lines:
        normalized_line = line.replace("：", ":")
        if ":" not in normalized_line:
            continue

        key_raw, value = normalized_line.split(":", 1)
        normalized_key = _normalize_key(key_raw.strip())
        if normalized_key in _FORBIDDEN_TYPED_IDENTITY_KEYS:
            raise DoctorDecisionParseError("unknown_field")
        parsed_key = _resolve_key(normalized_key)
        if parsed_key is None:
            raise DoctorDecisionParseError("unknown_field")
        if parsed_key in parsed_fields:
            raise DoctorDecisionParseError("duplicate_field")
        parsed_fields[parsed_key] = value.strip()

    for required_key in _REQUIRED_KEYS:
        if required_key not in parsed_fields:
            raise DoctorDecisionParseError(f"missing_{required_key}_line")

    decision_raw = _normalize_token(parsed_fields["decision"])
    decision = _DECISION_ALIASES.get(decision_raw)
    if decision is None:
        raise DoctorDecisionParseError("invalid_decision_value")

    support_flag = _resolve_support_flag(
        decision=decision,
        support_raw=parsed_fields.get("support_flag"),
    )
    admission_flow = _resolve_admission_flow(
        decision=decision,
        admission_flow_raw=parsed_fields.get("admission_flow"),
    )

    case_raw = parsed_fields["case_id"]
    case_match = _UUID_PATTERN.search(case_raw)
    if case_match is not None:
        case_raw = case_match.group(1)
    try:
        case_id = UUID(case_raw)
    except ValueError as error:
        raise DoctorDecisionParseError("invalid_case_line") from error
    if expected_case_id is not None and case_id != expected_case_id:
        raise DoctorDecisionParseError("case_id_mismatch")

    reason = None if decision == "accept" else _normalize_reason(parsed_fields.get("reason", ""))

    return DoctorDecisionReplyParsed(
        case_id=case_id,
        decision=decision,
        support_flag=support_flag,
        admission_flow=admission_flow,
        reason=reason,
    )


def _resolve_support_flag(*, decision: str, support_raw: str | None) -> str:
    if support_raw is None:
        if decision == "accept":
            raise DoctorDecisionParseError("missing_support_flag_line")
        return "none"

    support_flag = _SUPPORT_ALIASES.get(_normalize_token(support_raw))
    if support_flag is None:
        raise DoctorDecisionParseError("invalid_support_flag_value")
    if decision == "deny":
        return "none"
    return support_flag


def _resolve_admission_flow(*, decision: str, admission_flow_raw: str | None) -> str | None:
    if admission_flow_raw is None:
        if decision == "accept":
            raise DoctorDecisionParseError("missing_admission_flow_line")
        return None

    admission_flow = _ADMISSION_FLOW_ALIASES.get(_normalize_token(admission_flow_raw))
    if admission_flow is None:
        raise DoctorDecisionParseError("invalid_admission_flow_value")
    if decision == "deny":
        return None
    return admission_flow


def _normalize_key(raw_key: str) -> str:
    return _normalize_token(raw_key)


def _resolve_key(normalized_key: str) -> str | None:
    for canonical, aliases in _KEY_ALIASES.items():
        alias_set = {_normalize_token(alias) for alias in aliases}
        if normalized_key in alias_set:
            return canonical
    return None


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


def _normalize_reason(reason_raw: str) -> str | None:
    normalized = reason_raw.strip()
    if normalized.lower() in _EMPTY_REASON_MARKERS:
        return None
    return normalized


def _normalize_token(value: str) -> str:
    normalized = value.strip().lower()
    normalized = normalized.strip("`*_ ")
    normalized = normalized.replace("-", "_").replace("/", "_").replace(" ", "_")
    normalized = _strip_diacritics(normalized)
    normalized = re.sub(r"_+", "_", normalized)
    return normalized.strip("_")


def _strip_diacritics(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(character for character in decomposed if not unicodedata.combining(character))
