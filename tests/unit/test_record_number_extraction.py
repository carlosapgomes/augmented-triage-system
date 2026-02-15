from __future__ import annotations

import pytest

from triage_automation.domain.record_number import (
    RecordNumberExtractionError,
    extract_and_strip_agency_record_number,
)


def test_most_frequent_token_is_chosen() -> None:
    text = "12345 report 12345 data 99999 12345"

    result = extract_and_strip_agency_record_number(text)

    assert result.agency_record_number == "12345"


def test_all_occurrences_of_selected_token_are_removed() -> None:
    text = "12345 alpha 12345 beta 12345 gamma"

    result = extract_and_strip_agency_record_number(text)

    assert "12345" not in result.cleaned_text
    assert result.cleaned_text == "alpha beta gamma"


def test_tie_break_rule_is_deterministic() -> None:
    text = "54321 x 12345 y 54321 z 12345"

    result = extract_and_strip_agency_record_number(text)

    assert result.agency_record_number == "12345"


def test_no_five_digit_token_raises_error() -> None:
    with pytest.raises(RecordNumberExtractionError):
        extract_and_strip_agency_record_number("no watermark token here")
