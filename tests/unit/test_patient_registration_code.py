from __future__ import annotations

from triage_automation.domain.patient_registration_code import (
    count_patient_registration_codes,
    extract_patient_registration_codes,
    extract_patient_registration_matches,
)


def test_extract_codes_with_and_without_accent() -> None:
    text = "Codigo: 1234567\nCÓDIGO: 765432198"

    extracted = extract_patient_registration_codes(text)

    assert extracted == ["1234567", "765432198"]


def test_extract_matches_with_line_context() -> None:
    text = "linha 1\nCodigo: 123456789\ntexto\nCódigo: 123456789"

    matches = extract_patient_registration_matches(text)

    assert len(matches) == 2
    assert matches[0].line_number == 2
    assert matches[0].code == "123456789"
    assert "Codigo: 123456789" in matches[0].line_text
    assert matches[1].line_number == 4
    assert matches[1].code == "123456789"


def test_count_codes_tracks_frequency() -> None:
    text = "Codigo: 11111111\nCodigo: 222222222\nCódigo: 11111111"

    counts = count_patient_registration_codes(text)

    assert counts == {"11111111": 2, "222222222": 1}


def test_variable_digit_lengths_are_supported() -> None:
    text = "Codigo: 1234\nCodigo: 12345\nCodigo: 123456789\nCodigo: 7654321"

    extracted = extract_patient_registration_codes(text)

    assert extracted == ["12345", "123456789", "7654321"]


def test_extract_code_from_report_header_flow() -> None:
    text = "RELATÓRIO DE OCORRÊNCIAS\n123456789\nobservação"

    extracted = extract_patient_registration_codes(text)

    assert extracted == ["123456789"]


def test_report_header_match_uses_code_line_context() -> None:
    text = "cabecalho\nRELATORIO DE OCORRENCIAS:\nregistro 7654321\nfim"

    matches = extract_patient_registration_matches(text)

    assert len(matches) == 1
    assert matches[0].code == "7654321"
    assert matches[0].line_number == 3
    assert matches[0].line_text == "registro 7654321"
