"""Domain logic for extracting and stripping agency record number watermark."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

from triage_automation.domain.patient_registration_code import extract_patient_registration_codes


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
