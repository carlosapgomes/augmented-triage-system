from __future__ import annotations

from datetime import datetime
from uuid import UUID

from triage_automation.infrastructure.matrix.message_templates import (
    build_room1_final_accepted_message,
    build_room1_final_denied_triage_message,
    build_room1_final_failure_message,
    build_room1_final_immediate_message,
    build_room3_ack_message,
    build_room3_immediate_admission_message,
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

    assert "## no. ocorrência: 4777300" in body
    assert "## paciente: MARIA" in body
    assert "idade: 42" in body
    assert "exame solicitado: EDA" in body
    assert "aceito por: não informado" in body
    assert f"caso: {case_id}" not in body


def test_build_room3_request_message_includes_doctor_display_name_when_provided() -> None:
    case_id = UUID("11111111-1111-1111-1111-111111111111")

    body = build_room3_request_message(
        case_id=case_id,
        agency_record_number="4777300",
        patient_name="MARIA",
        patient_age="42",
        requested_exam="EDA",
        doctor_display_name="Dr. João Pereira",
    )

    assert "aceito por: Dr. João Pereira" in body


def test_build_room3_request_message_includes_pediatric_context_when_flagged() -> None:
    case_id = UUID("12121212-1212-1212-1212-121212121212")

    body = build_room3_request_message(
        case_id=case_id,
        agency_record_number="4821526",
        patient_name="EMANUELLE VITORIA CASTRO PEREIRA",
        patient_age="1",
        requested_exam="Endoscopia digestiva alta",
        doctor_display_name="admin",
        pediatric_flag=True,
    )

    assert "idade: 1" in body
    assert "exame solicitado: Endoscopia digestiva alta" in body
    assert "paciente pediátrico: sim" in body
    assert "aceito por: admin" in body


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


def test_build_room3_immediate_admission_message_includes_immediate_context() -> None:
    body = build_room3_immediate_admission_message(
        agency_record_number="4777300",
        patient_name="MARIA",
        patient_age="12",
        requested_exam="EDA para retirada de corpo estranho",
        doctor_display_name="Dra. Beatriz Silva",
        support_flag="anesthesist_icu",
        supported_eda_subtype="foreign_body",
        pediatric_flag=True,
    )

    assert "idade: 12" in body
    assert "exame solicitado: EDA para retirada de corpo estranho" in body
    assert "subtipo EDA: retirada de corpo estranho" in body
    assert "paciente pediátrico: sim" in body
    assert "aceito por: Dra. Beatriz Silva" in body
    assert "suporte: anestesista_uti" in body


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


def test_build_room1_final_accepted_message_includes_shared_immediate_context() -> None:
    case_id = UUID("77777777-7777-7777-7777-777777777777")

    body = build_room1_final_accepted_message(
        case_id=case_id,
        agency_record_number="777002",
        patient_name="PACIENTE APTO",
        patient_age="12",
        requested_exam="EDA para retirada de corpo estranho",
        appointment_at=datetime(2026, 2, 16, 14, 30),
        location="Sala 2",
        instructions="Jejum 8h",
        doctor_display_name="Dra. Beatriz Silva",
        support_flag="anesthesist_icu",
        supported_eda_subtype="foreign_body",
        pediatric_flag=True,
    )

    assert "subtipo EDA: retirada de corpo estranho" in body
    assert "paciente pediátrico: sim" in body
    assert "aceito por: Dra. Beatriz Silva" in body
    assert "suporte: anestesista_uti" in body


def test_build_room1_final_immediate_message_uses_context_without_scheduling_lines() -> None:
    case_id = UUID("88888888-8888-8888-8888-888888888888")

    body = build_room1_final_immediate_message(
        case_id=case_id,
        agency_record_number="777006",
        patient_name="PACIENTE IMEDIATO",
        patient_age="12",
        requested_exam="EDA para retirada de corpo estranho",
        doctor_display_name="Dra. Beatriz Silva",
        support_flag="anesthesist_icu",
        supported_eda_subtype="foreign_body",
        pediatric_flag=True,
    )

    assert "✅ aceito com vinda imediata autorizada" in body
    assert "subtipo EDA: retirada de corpo estranho" in body
    assert "paciente pediátrico: sim" in body
    assert "aceito por: Dra. Beatriz Silva" in body
    assert "suporte: anestesista_uti" in body
    assert "agendamento:" not in body
    assert "local:" not in body
    assert "instrucoes:" not in body
    assert f"caso: {case_id}" not in body


def test_build_room1_final_denied_triage_message_does_not_include_doctor_line() -> None:
    case_id = UUID("66666666-6666-6666-6666-666666666666")

    body = build_room1_final_denied_triage_message(
        case_id=case_id,
        agency_record_number="777001",
        patient_name="PACIENTE TRIAGEM",
        patient_age="51",
        requested_exam="EDA",
        reason="critério clínico",
    )

    assert "no. ocorrência: 777001" in body
    assert "paciente: PACIENTE TRIAGEM" in body
    assert "aceito por:" not in body


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
