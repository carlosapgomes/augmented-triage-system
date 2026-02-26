from __future__ import annotations

from datetime import datetime
from uuid import UUID

from triage_automation.infrastructure.matrix.message_templates import (
    build_room1_final_accepted_message,
    build_room1_final_failure_message,
    build_room3_ack_message,
    build_room3_invalid_format_reprompt,
    build_room3_reply_template_message,
    build_room3_request_message,
)


def test_build_room3_request_message_prioritizes_human_identification_without_uuid() -> None:
    case_id = UUID("11111111-1111-1111-1111-111111111111")

    body = build_room3_request_message(
        case_id=case_id,
        agency_record_number="4777300",
        patient_name="MARIA",
        patient_age="42",
        requested_exam="EDA",
    )

    assert "no. ocorrência: 4777300" in body
    assert "paciente: MARIA" in body
    assert "idade: 42" in body
    assert "exame solicitado: EDA" in body
    assert f"caso: {case_id}" not in body


def test_build_room3_ack_message_prioritizes_human_identification_without_uuid() -> None:
    case_id = UUID("11111111-1111-1111-1111-111111111111")

    body = build_room3_ack_message(
        case_id=case_id,
        agency_record_number="4777300",
        patient_name="MARIA",
        patient_age="42",
        requested_exam="EDA",
    )

    assert "no. ocorrência: 4777300" in body
    assert "paciente: MARIA" in body
    assert "idade: 42" in body
    assert "exame solicitado: EDA" in body
    assert f"caso: {case_id}" not in body


def test_build_room3_reply_template_message_keeps_uuid_and_adds_human_identification() -> None:
    case_id = UUID("22222222-2222-2222-2222-222222222222")

    body = build_room3_reply_template_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
    )

    assert "no. ocorrência: 12345" in body
    assert "paciente: JOSE" in body
    assert f"caso: {case_id}" in body


def test_build_room3_invalid_format_reprompt_keeps_uuid_and_fallback_identification() -> None:
    case_id = UUID("33333333-3333-3333-3333-333333333333")

    body = build_room3_invalid_format_reprompt(
        case_id=case_id,
        agency_record_number=None,
        patient_name="",
    )

    assert "no. ocorrência: não detectado" in body
    assert "paciente: não detectado" in body
    assert f"caso: {case_id}" in body


def test_build_room1_final_accepted_message_prioritizes_human_identification_without_uuid() -> None:
    case_id = UUID("44444444-4444-4444-4444-444444444444")

    body = build_room1_final_accepted_message(
        case_id=case_id,
        agency_record_number="777002",
        patient_name="PACIENTE APTO",
        patient_age="62",
        requested_exam="EDA",
        appointment_at=datetime(2026, 2, 16, 14, 30),
        location="Sala 2",
        instructions="Jejum 8h",
    )

    assert "no. ocorrência: 777002" in body
    assert "paciente: PACIENTE APTO" in body
    assert f"caso: {case_id}" not in body


def test_build_room1_final_failure_message_uses_human_identification_fallback() -> None:
    case_id = UUID("55555555-5555-5555-5555-555555555555")

    body = build_room1_final_failure_message(
        case_id=case_id,
        agency_record_number=None,
        patient_name=None,
        patient_age=None,
        requested_exam=None,
        cause="llm",
        details="schema mismatch",
    )

    assert "no. ocorrência: não detectado" in body
    assert "paciente: não detectado" in body
    assert "idade: (vazio)" in body
    assert "exame solicitado: (vazio)" in body
    assert f"caso: {case_id}" not in body
