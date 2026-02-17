from __future__ import annotations

import pytest

from triage_automation.domain import record_number as record_number_module
from triage_automation.domain.record_number import extract_and_strip_agency_record_number


def test_extracts_from_report_header_flow() -> None:
    text = "RELATÓRIO DE OCORRÊNCIAS 4775652 paciente dados"

    result = extract_and_strip_agency_record_number(text)

    assert result.agency_record_number == "4775652"


def test_all_occurrences_of_selected_token_are_removed() -> None:
    text = "RELATÓRIO DE OCORRÊNCIAS 4775652 alpha 4775652 beta"

    result = extract_and_strip_agency_record_number(text)

    assert "4775652" not in result.cleaned_text


def test_cleaning_preserves_linebreaks_after_watermark_removal() -> None:
    text = (
        "RELATÓRIO DE OCORRÊNCIAS 4775652\n"
        "Linha clínica 1 4775652\n"
        "Linha clínica 2"
    )

    result = extract_and_strip_agency_record_number(text)

    assert "4775652" not in result.cleaned_text
    assert result.cleaned_text.count("\n") >= 2


def test_removes_repeated_five_digit_watermark_blocks_and_residual_tokens() -> None:
    text = (
        "RELATÓRIO DE OCORRÊNCIAS 4762341\n"
        "63625 63625 63625 63625 63625\n"
        "63625 63625 63625 63625 63625\n"
        "Nome Social:\n"
        "63625\n"
        "Motivo da Solicitação: Endoscopia Digestiva Alta - EDA\n"
    )

    result = extract_and_strip_agency_record_number(text)

    assert result.agency_record_number == "4762341"
    assert "63625" not in result.cleaned_text
    assert "Motivo da Solicitação" in result.cleaned_text


def test_prefers_explicit_registration_over_repeated_watermark() -> None:
    text = "RELATÓRIO DE OCORRÊNCIAS 4775652 ... 40371 40371 40371"

    result = extract_and_strip_agency_record_number(text)

    assert result.agency_record_number == "4775652"


def test_no_supported_pattern_falls_back_to_epoch_millis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(record_number_module, "_current_epoch_millis", lambda: 1735689600123)

    result = extract_and_strip_agency_record_number("no registration anchor here 40371 40371")

    assert result.agency_record_number == "1735689600123"
    assert result.cleaned_text == "no registration anchor here 40371 40371"
