from __future__ import annotations

from uuid import UUID

import pytest

from triage_automation.domain.doctor_decision_parser import (
    DoctorDecisionParseError,
    parse_doctor_decision_reply,
)

CASE_ID = "11111111-1111-1111-1111-111111111111"


def test_parse_accept_template_success_with_scheduled_admission_flow() -> None:
    body = (
        "decisao: aceitar\n"
        "fluxo de admissao: agendamento\n"
        "suporte: anestesista\n"
        "motivo: risco cardiovascular moderado\n"
        f"caso: {CASE_ID}\n"
    )

    parsed = parse_doctor_decision_reply(body=body)

    assert str(parsed.case_id) == CASE_ID
    assert parsed.decision == "accept"
    assert parsed.admission_flow == "scheduled"
    assert parsed.support_flag == "anesthesist"
    assert parsed.reason is None


def test_parse_deny_template_allows_missing_support_and_admission_flow() -> None:
    body = (
        "decisao: negar\n"
        "motivo:\n"
        f"caso: {CASE_ID}\n"
    )

    parsed = parse_doctor_decision_reply(body=body)

    assert parsed.decision == "deny"
    assert parsed.support_flag == "none"
    assert parsed.admission_flow is None
    assert parsed.reason is None


def test_parse_deny_ignores_valid_support_and_admission_flow_semantically() -> None:
    body = (
        "decisao: negar\n"
        "fluxo_admissao: vinda_imediata\n"
        "suporte: anestesista\n"
        "motivo: nao autorizado\n"
        f"caso: {CASE_ID}\n"
    )

    parsed = parse_doctor_decision_reply(body=body)

    assert parsed.decision == "deny"
    assert parsed.support_flag == "none"
    assert parsed.admission_flow is None
    assert parsed.reason == "nao autorizado"


def test_parse_accepts_legacy_english_keys_with_normalized_admission_flow() -> None:
    body = (
        "decision: accept\n"
        "admission_flow: immediate\n"
        "support_flag: none\n"
        "reason: ok\n"
        f"case_id: {CASE_ID}\n"
    )

    parsed = parse_doctor_decision_reply(body=body)

    assert parsed.decision == "accept"
    assert parsed.admission_flow == "immediate"
    assert parsed.support_flag == "none"
    assert parsed.reason is None


def test_parse_accepts_without_space_after_colon_and_immediate_alias() -> None:
    body = (
        "decisao:aceitar\n"
        "fluxo_admissao:vinda imediata\n"
        "suporte:nenhum\n"
        f"caso:{CASE_ID}\n"
    )

    parsed = parse_doctor_decision_reply(body=body)

    assert parsed.decision == "accept"
    assert parsed.admission_flow == "immediate"
    assert parsed.support_flag == "none"
    assert parsed.reason is None


def test_parse_accepts_template_wrapped_in_code_fences() -> None:
    body = (
        "```text\n"
        "decisao: aceitar\n"
        "fluxo de admissao: agendamento\n"
        "suporte: nenhum\n"
        f"caso: {CASE_ID}\n"
        "```\n"
    )

    parsed = parse_doctor_decision_reply(body=body)

    assert parsed.decision == "accept"
    assert parsed.admission_flow == "scheduled"
    assert parsed.support_flag == "none"


def test_parse_accepts_key_with_accented_admission_flow_alias() -> None:
    body = (
        "decisão: aceitar\n"
        "fluxo de admissão: vinda_imediata\n"
        "suporte: nenhum\n"
        f"caso: {CASE_ID}\n"
    )

    parsed = parse_doctor_decision_reply(body=body)

    assert parsed.decision == "accept"
    assert parsed.admission_flow == "immediate"


def test_parse_rejects_unknown_labeled_field() -> None:
    body = (
        "decisao: aceitar\n"
        "fluxo de admissao: agendamento\n"
        "suporte: nenhum\n"
        "campo_extra: 123\n"
        f"caso: {CASE_ID}\n"
    )

    with pytest.raises(DoctorDecisionParseError, match="unknown_field"):
        parse_doctor_decision_reply(body=body)


def test_parse_rejects_missing_admission_flow_for_accept() -> None:
    body = (
        "decisao: aceitar\n"
        "suporte: nenhum\n"
        f"caso: {CASE_ID}\n"
    )

    with pytest.raises(DoctorDecisionParseError, match="missing_admission_flow_line"):
        parse_doctor_decision_reply(body=body)


def test_parse_rejects_invalid_case_uuid() -> None:
    body = (
        "decisao: aceitar\n"
        "fluxo de admissao: agendamento\n"
        "suporte: nenhum\n"
        "caso: not-a-uuid\n"
    )

    with pytest.raises(DoctorDecisionParseError, match="invalid_case_line"):
        parse_doctor_decision_reply(body=body)


def test_parse_rejects_case_id_mismatch() -> None:
    body = (
        "decisao: aceitar\n"
        "fluxo de admissao: agendamento\n"
        "suporte: nenhum\n"
        f"caso: {CASE_ID}\n"
    )

    with pytest.raises(DoctorDecisionParseError, match="case_id_mismatch"):
        parse_doctor_decision_reply(
            body=body,
            expected_case_id=UUID("22222222-2222-2222-2222-222222222222"),
        )


def test_parse_rejects_invalid_admission_flow_value() -> None:
    body = (
        "decisao: aceitar\n"
        "fluxo de admissao: plantao\n"
        "suporte: nenhum\n"
        f"caso: {CASE_ID}\n"
    )

    with pytest.raises(DoctorDecisionParseError, match="invalid_admission_flow_value"):
        parse_doctor_decision_reply(body=body)


def test_parse_rejects_typed_doctor_user_id_field() -> None:
    body = (
        "decisao: aceitar\n"
        "fluxo de admissao: agendamento\n"
        "suporte: nenhum\n"
        "doctor_user_id: @doctor:example.org\n"
        f"caso: {CASE_ID}\n"
    )

    with pytest.raises(DoctorDecisionParseError, match="unknown_field"):
        parse_doctor_decision_reply(body=body)


def test_parse_ignores_non_labeled_extra_line() -> None:
    body = (
        "texto livre sem campo\n"
        "decisao: aceitar\n"
        "fluxo de admissao: agendamento\n"
        "suporte: nenhum\n"
        f"caso: {CASE_ID}\n"
    )

    parsed = parse_doctor_decision_reply(body=body)

    assert parsed.decision == "accept"
    assert parsed.admission_flow == "scheduled"
    assert parsed.support_flag == "none"


def test_parse_rejects_invalid_decision_enum_value() -> None:
    body = (
        "decisao: talvez\n"
        "fluxo de admissao: agendamento\n"
        "suporte: nenhum\n"
        f"caso: {CASE_ID}\n"
    )

    with pytest.raises(DoctorDecisionParseError, match="invalid_decision_value"):
        parse_doctor_decision_reply(body=body)


def test_parse_rejects_invalid_support_flag_enum_value() -> None:
    body = (
        "decisao: aceitar\n"
        "fluxo de admissao: agendamento\n"
        "suporte: cirurgiao\n"
        f"caso: {CASE_ID}\n"
    )

    with pytest.raises(DoctorDecisionParseError, match="invalid_support_flag_value"):
        parse_doctor_decision_reply(body=body)
