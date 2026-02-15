"""Domain logic for extracting and stripping agency record number watermark."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass


class RecordNumberExtractionError(ValueError):
    """Raised when no valid repeated 5-digit watermark can be extracted."""


@dataclass(frozen=True)
class RecordNumberExtractionResult:
    """Extracted agency record number and cleaned text payload."""

    agency_record_number: str
    cleaned_text: str


def extract_and_strip_agency_record_number(text: str) -> RecordNumberExtractionResult:
    """Extract most frequent 5-digit token and remove all its occurrences from text."""

    tokens = re.findall(r"\b\d{5}\b", text)
    if not tokens:
        raise RecordNumberExtractionError("No 5-digit agency record number found")

    frequency = Counter(tokens)
    max_frequency = max(frequency.values())
    candidates = sorted(token for token, count in frequency.items() if count == max_frequency)
    selected = candidates[0]

    cleaned_text = re.sub(rf"\b{re.escape(selected)}\b", " ", text)
    normalized_text = " ".join(cleaned_text.split())

    return RecordNumberExtractionResult(
        agency_record_number=selected,
        cleaned_text=normalized_text,
    )
