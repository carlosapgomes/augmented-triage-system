from __future__ import annotations

from uuid import uuid4

from triage_automation.domain.scheduler_parser import parse_scheduler_reply


def test_confirmed_template_parses_required_fields() -> None:
    case_id = uuid4()
    body = (
        "16-02-2026 14:30 BRT\n"
        "location: Sala 2\n"
        "instructions: Jejum 8h\n"
        f"case: {case_id}\n"
    )

    parsed = parse_scheduler_reply(body=body, expected_case_id=case_id)

    assert parsed.appointment_status == "confirmed"
    assert parsed.case_id == case_id
    assert parsed.location == "Sala 2"
    assert parsed.instructions == "Jejum 8h"
    assert parsed.appointment_at is not None
    assert parsed.appointment_at.tzinfo is not None


def test_denied_template_parses_required_fields() -> None:
    case_id = uuid4()
    body = f"denied\nreason: sem agenda\ncase: {case_id}\n"

    parsed = parse_scheduler_reply(body=body, expected_case_id=case_id)

    assert parsed.appointment_status == "denied"
    assert parsed.case_id == case_id
    assert parsed.reason == "sem agenda"
    assert parsed.appointment_at is None
    assert parsed.location is None
    assert parsed.instructions is None


def test_confirmed_template_with_header_parses_required_fields() -> None:
    case_id = uuid4()
    body = (
        "Confirmed:\n"
        "22-02-2026 15:30 BRT\n"
        "location: CHD HGRS\n"
        "instructions: jejum de 06 horas\n"
        f"case: {case_id}\n"
    )

    parsed = parse_scheduler_reply(body=body, expected_case_id=case_id)

    assert parsed.appointment_status == "confirmed"
    assert parsed.case_id == case_id
    assert parsed.location == "CHD HGRS"
    assert parsed.instructions == "jejum de 06 horas"
    assert parsed.appointment_at is not None


def test_denied_template_with_header_parses_required_fields() -> None:
    case_id = uuid4()
    body = (
        "Denied:\n"
        "denied\n"
        "reason: sem agenda na data\n"
        f"case: {case_id}\n"
    )

    parsed = parse_scheduler_reply(body=body, expected_case_id=case_id)

    assert parsed.appointment_status == "denied"
    assert parsed.case_id == case_id
    assert parsed.reason == "sem agenda na data"


def test_confirmed_template_in_portuguese_parses_required_fields() -> None:
    case_id = uuid4()
    body = (
        "Confirmado:\n"
        "22-02-2026 15:30 BRT\n"
        "local: CHD HGRS\n"
        "instrucoes: jejum de 06 horas\n"
        f"caso: {case_id}\n"
    )

    parsed = parse_scheduler_reply(body=body, expected_case_id=case_id)

    assert parsed.appointment_status == "confirmed"
    assert parsed.case_id == case_id
    assert parsed.location == "CHD HGRS"
    assert parsed.instructions == "jejum de 06 horas"
    assert parsed.appointment_at is not None


def test_denied_template_in_portuguese_parses_required_fields() -> None:
    case_id = uuid4()
    body = (
        "Negado:\n"
        "negado\n"
        "motivo: sem agenda na data\n"
        f"caso: {case_id}\n"
    )

    parsed = parse_scheduler_reply(body=body, expected_case_id=case_id)

    assert parsed.appointment_status == "denied"
    assert parsed.case_id == case_id
    assert parsed.reason == "sem agenda na data"
