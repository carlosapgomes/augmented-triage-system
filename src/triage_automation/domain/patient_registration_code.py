"""Helpers to detect patient registration code patterns in extracted text."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

_CODE_LABEL_PATTERN = re.compile(
    r"\bC(?:[oO]|[óÓ])digo\s*:\s*([0-9]{5,})\b",
    flags=re.IGNORECASE,
)

_REPORT_HEADER_FLOW_PATTERN = re.compile(
    r"RELAT(?:[OÓ])RIO\s+DE\s+OCORR(?:[EÊ])NCIAS"
    r"(?:\s*[:\-])?"
    r"[\s\S]{0,120}?"
    r"\b([0-9]{5,})\b",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class PatientRegistrationCodeMatch:
    """One pattern match with source line context."""

    code: str
    line_number: int
    line_text: str


def _line_context_for_index(text: str, index: int) -> tuple[int, str]:
    line_start = text.rfind("\n", 0, index) + 1
    line_end = text.find("\n", index)
    if line_end == -1:
        line_end = len(text)
    line_number = text.count("\n", 0, index) + 1
    return line_number, text[line_start:line_end].strip()


def _iter_code_matches(text: str) -> list[PatientRegistrationCodeMatch]:
    seen: set[tuple[int, str]] = set()
    ordered: list[tuple[int, PatientRegistrationCodeMatch]] = []

    for pattern in (_CODE_LABEL_PATTERN, _REPORT_HEADER_FLOW_PATTERN):
        for pattern_match in pattern.finditer(text):
            code = pattern_match.group(1)
            code_start = pattern_match.start(1)
            unique_key = (code_start, code)
            if unique_key in seen:
                continue
            seen.add(unique_key)
            line_number, line_text = _line_context_for_index(text, code_start)
            ordered.append(
                (
                    code_start,
                    PatientRegistrationCodeMatch(
                        code=code,
                        line_number=line_number,
                        line_text=line_text,
                    ),
                )
            )

    ordered.sort(key=lambda item: item[0])
    return [item[1] for item in ordered]


def extract_patient_registration_codes(text: str) -> list[str]:
    """Extract all supported patient registration code occurrences from text."""

    return [match.code for match in _iter_code_matches(text)]


def extract_patient_registration_matches(text: str) -> list[PatientRegistrationCodeMatch]:
    """Extract all supported pattern matches with line metadata for diagnostics."""

    return _iter_code_matches(text)


def count_patient_registration_codes(text: str) -> dict[str, int]:
    """Count occurrences of each extracted patient registration code."""

    return dict(Counter(extract_patient_registration_codes(text)))
