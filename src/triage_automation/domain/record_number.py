"""Domain logic for extracting and stripping agency record number watermark."""

from __future__ import annotations

import re
import time
from collections import Counter
from dataclasses import dataclass

from triage_automation.domain.patient_registration_code import extract_patient_registration_codes

_REPEATED_FIVE_DIGIT_LINE_PATTERN = re.compile(r"^\s*(\d{5})(?:\s+\1){3,}\s*$")
_FIVE_DIGIT_TOKEN_PATTERN = re.compile(r"\b(\d{5})\b")


@dataclass(frozen=True)
class RecordNumberExtractionResult:
    """Extracted agency record number and cleaned text payload."""

    agency_record_number: str
    cleaned_text: str


def extract_and_strip_agency_record_number(text: str) -> RecordNumberExtractionResult:
    """Extract agency record number and remove all its occurrences from text.

    Strategy:
    1. Prefer explicit patient registration patterns from extracted document flow.
    2. Fallback to current epoch in milliseconds when none is found.
    """

    explicit_codes = extract_patient_registration_codes(text)
    selected = explicit_codes[0] if explicit_codes else str(_current_epoch_millis())

    cleaned_text = re.sub(rf"\b{re.escape(selected)}\b", " ", text)
    cleaned_text = _strip_repeated_five_digit_watermarks(
        cleaned_text,
        protected_token=selected,
    )
    normalized_text = _normalize_preserving_linebreaks(cleaned_text)

    return RecordNumberExtractionResult(
        agency_record_number=selected,
        cleaned_text=normalized_text,
    )


def _current_epoch_millis() -> int:
    """Return current UNIX epoch in milliseconds."""

    return time.time_ns() // 1_000_000


def _normalize_preserving_linebreaks(text: str) -> str:
    """Normalize spaces while preserving paragraph linebreaks."""

    normalized_lines: list[str] = []
    for raw_line in text.splitlines():
        compact = re.sub(r"[ \t]+", " ", raw_line).strip()
        if not compact:
            if normalized_lines and normalized_lines[-1] != "":
                normalized_lines.append("")
            continue
        normalized_lines.append(compact)

    return "\n".join(normalized_lines).strip()


def _strip_repeated_five_digit_watermarks(text: str, *, protected_token: str) -> str:
    """Remove repeated 5-digit watermark bands and residual isolated tokens."""

    lines = text.splitlines()
    repeated_line_token_counts: Counter[str] = Counter()
    for line in lines:
        match = _REPEATED_FIVE_DIGIT_LINE_PATTERN.match(line)
        if match is None:
            continue
        repeated_line_token_counts[match.group(1)] += 1

    candidate_tokens = {
        token for token, count in repeated_line_token_counts.items() if count >= 1
    }
    candidate_tokens.discard(protected_token)
    if not candidate_tokens:
        return text

    filtered_lines: list[str] = []
    for line in lines:
        match = _REPEATED_FIVE_DIGIT_LINE_PATTERN.match(line)
        if match is not None and match.group(1) in candidate_tokens:
            continue
        filtered_lines.append(line)

    partially_cleaned = "\n".join(filtered_lines)
    token_counts = Counter(_FIVE_DIGIT_TOKEN_PATTERN.findall(partially_cleaned))
    removable_tokens = {
        token for token in candidate_tokens if token_counts.get(token, 0) >= 1
    }
    if not removable_tokens:
        return partially_cleaned

    result = partially_cleaned
    for token in removable_tokens:
        result = re.sub(rf"\b{re.escape(token)}\b", " ", result)
    return result
