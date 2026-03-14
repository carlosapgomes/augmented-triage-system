from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from triage_automation.infrastructure.matrix.message_templates import (
    build_room2_case_decision_instructions_formatted_html,
    build_room2_case_decision_instructions_message,
    build_room2_case_decision_template_formatted_html,
    build_room2_case_decision_template_message,
    build_room2_case_pdf_attachment_filename,
    build_room2_case_pdf_formatted_html,
    build_room2_case_pdf_message,
    build_room2_case_summary_formatted_html,
    build_room2_case_summary_message,
    build_room2_decision_ack_message,
    build_room2_decision_error_message,
)


def _extract_markdown_section_lines(
    *,
    body: str,
    section: str,
    next_section: str | None,
) -> list[str]:
    start = body.index(section) + len(section)
    if next_section is None:
        end = len(body)
    else:
        end = body.index(next_section, start)
    chunk = body[start:end]
    return [line.strip() for line in chunk.splitlines() if line.strip()]


def _extract_html_section_chunk(
    *,
    body: str,
    section: str,
    next_section: str | None,
) -> str:
    start = body.index(section) + len(section)
    if next_section is None:
        end = len(body)
    else:
        end = body.index(next_section, start)
    return body[start:end]


def test_build_room2_case_pdf_message_includes_compact_context_and_attachment_hint() -> None:
    case_id = UUID("11111111-1111-1111-1111-111111111111")

    body = build_room2_case_pdf_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="MARIA",
        extracted_text="Paciente com dispepsia crônica.",
    )

    assert "no. ocorrência: 12345" in body
    assert "paciente: MARIA" in body
    assert f"caso: {case_id}" not in body
    assert "PDF original do relatório" in body


def test_build_room2_case_pdf_formatted_html_includes_preview_context() -> None:
    case_id = UUID("11111111-1111-1111-1111-111111111111")

    body = build_room2_case_pdf_formatted_html(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="MARIA",
        extracted_text="Linha 1\nLinha 2",
    )

    assert "<h1>Solicitação de triagem - contexto original</h1>" in body
    assert "<p>no. ocorrência: 12345</p>" in body
    assert "<p>paciente: MARIA</p>" in body
    assert f"<p>caso: {case_id}</p>" not in body
    assert "PDF original do relatório" in body


def test_build_room2_case_pdf_attachment_filename_is_deterministic() -> None:
    case_id = UUID("11111111-1111-1111-1111-111111111111")

    filename = build_room2_case_pdf_attachment_filename(
        case_id=case_id,
        agency_record_number="4777300",
    )

    assert (
        filename
        == "ocorrencia-4777300-caso-11111111-1111-1111-1111-111111111111-relatorio-original.pdf"
    )


def test_build_room2_case_pdf_attachment_filename_uses_fallback_when_record_missing() -> None:
    case_id = UUID("11111111-1111-1111-1111-111111111111")

    filename = build_room2_case_pdf_attachment_filename(
        case_id=case_id,
        agency_record_number=" ",
    )

    assert (
        filename
        == (
            "ocorrencia-indisponivel-caso-11111111-1111-1111-1111-111111111111-"
            "relatorio-original.pdf"
        )
    )


def test_build_room2_case_summary_message_avoids_full_flattened_dump() -> None:
    case_id = UUID("22222222-2222-2222-2222-222222222222")

    body = build_room2_case_summary_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="PACIENTE",
        structured_data={
            "policy_precheck": {
                "labs_pass": "yes",
                "ecg_present": "no",
                "labs_failed_items": ["INR ausente"],
            },
            "eda": {
                "labs": {"hb_g_dl": 10.2, "platelets_per_mm3": 140000, "inr": None},
                "ecg": {"report_present": "no", "abnormal_flag": "unknown"},
            },
        },
        summary_text="Resumo LLM1",
        suggested_action={"suggestion": "accept", "support_recommendation": "none"},
    )

    assert "## no. ocorrência: 12345" in body
    assert "## paciente: PACIENTE" in body
    assert f"caso: {case_id}" not in body
    assert "Resumo LLM1" in body
    assert "# Resumo técnico da triagem" in body
    assert "## Resumo clínico:" in body
    assert "## Achados críticos:" in body
    assert "## Pendências críticas:" in body
    assert "## Decisão sugerida:" in body
    assert "## Suporte recomendado:" in body
    assert "## Motivo objetivo:" in body
    assert "## Conduta sugerida:" not in body
    assert "## Dados extraídos:" not in body
    assert "## Recomendação do sistema:" not in body
    section_order = [
        "## Resumo clínico:",
        "## Achados críticos:",
        "## Pendências críticas:",
        "## Decisão sugerida:",
        "## Suporte recomendado:",
        "## Motivo objetivo:",
    ]
    section_positions = [body.index(section) for section in section_order]
    assert section_positions == sorted(section_positions)
    assert "- Hb: 10.2" in body
    assert "- Plaquetas: 140000" in body
    assert "- INR: não informado" in body
    assert "- ECG presente: nao" in body
    assert "- ECG sinal de alerta: indeterminado (sem evidência no laudo)" in body
    assert "- Laboratório obrigatório (pré-check): sim" in body
    assert "- ECG obrigatório (pré-check): nao" in body
    assert "- Pendências de laboratório: INR ausente" in body
    assert "flag_pediatrico" not in body
    assert "abnormal_flag" not in body
    assert "prechecagem_politica:" not in body
    assert "asa.classe=" not in body
    assert "ecg.sinal de alerta=" not in body
    assert "aceitar" in body
    assert "accept" not in body
    assert "Achados críticos" in body
    assert "Conduta sugerida" not in body
    assert "```json" not in body


def test_build_room2_case_summary_formats_recent_denial_datetime_in_brt() -> None:
    case_id = UUID("22222222-2222-2222-2222-222222222222")

    body = build_room2_case_summary_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="PACIENTE",
        structured_data={
            "policy_precheck": {
                "labs_pass": "yes",
                "ecg_present": "yes",
                "labs_failed_items": [],
            },
            "eda": {
                "labs": {"hb_g_dl": 10.2, "platelets_per_mm3": 140000, "inr": 1.2},
                "ecg": {"report_present": "yes", "abnormal_flag": "no"},
            },
        },
        summary_text="Resumo LLM1",
        suggested_action={"suggestion": "accept", "support_recommendation": "none"},
        recent_denial_context={
            "decision": "deny_triage",
            "reason": "criterio clinico",
            "decided_at": datetime(2026, 2, 15, 15, 30, tzinfo=UTC),
            "prior_denial_count_7d": 2,
        },
    )

    assert "## Histórico de negativa recente:" in body
    assert "- Data/hora da negativa mais recente: 15/02/2026 12:30 BRT" in body


def test_build_room2_case_summary_formatted_html_formats_recent_denial_datetime_in_brt() -> None:
    case_id = UUID("22222222-2222-2222-2222-222222222222")

    body = build_room2_case_summary_formatted_html(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="PACIENTE",
        structured_data={
            "policy_precheck": {
                "labs_pass": "yes",
                "ecg_present": "yes",
                "labs_failed_items": [],
            },
            "eda": {
                "labs": {"hb_g_dl": 10.2, "platelets_per_mm3": 140000, "inr": 1.2},
                "ecg": {"report_present": "yes", "abnormal_flag": "no"},
            },
        },
        summary_text="Resumo LLM1",
        suggested_action={"suggestion": "accept", "support_recommendation": "none"},
        recent_denial_context={
            "decision": "deny_appointment",
            "reason": "agenda",
            "decided_at": datetime(2026, 2, 15, 15, 30, tzinfo=UTC),
            "prior_denial_count_7d": 1,
        },
    )

    assert "<h2>Histórico de negativa recente:</h2>" in body
    assert "Data/hora da negativa mais recente: 15/02/2026 12:30 BRT" in body


def test_build_room2_case_decision_instructions_message_has_strict_template() -> None:
    case_id = UUID("33333333-3333-3333-3333-333333333333")

    body = build_room2_case_decision_instructions_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="PACIENTE",
    )

    assert "copie a próxima mensagem" in body.lower()
    assert "responda como resposta a ela" in body.lower()
    assert "decisão:aceitar" in body
    assert "valores válidos" in body.lower()
    assert "no. ocorrência: 12345" in body
    assert "paciente: PACIENTE" in body
    assert "caso esperado" not in body


def test_build_room2_case_decision_instructions_formatted_html_has_guidance() -> None:
    case_id = UUID("33333333-3333-3333-3333-333333333333")

    body = build_room2_case_decision_instructions_formatted_html(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="PACIENTE",
    )

    assert "<h1>Instrução de decisão médica</h1>" in body
    assert "<ol>" in body
    assert "Copie a <strong>PRÓXIMA mensagem</strong>" in body
    assert "<p>no. ocorrência: 12345<br>paciente: PACIENTE</p>" in body
    assert "decisão:aceitar" in body


def test_build_room2_case_decision_template_message_is_copy_paste_ready() -> None:
    case_id = UUID("33333333-3333-3333-3333-333333333333")

    body = build_room2_case_decision_template_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="PACIENTE",
    )

    assert body.startswith("no. ocorrência: 12345\npaciente: PACIENTE\n")
    assert "decisao: aceitar\n" in body
    assert "suporte: nenhum\n" in body
    assert "motivo: (opcional)\n" in body
    assert body.endswith(f"caso: {case_id}")


def test_build_room2_case_decision_template_formatted_html_has_plain_lines() -> None:
    case_id = UUID("33333333-3333-3333-3333-333333333333")

    body = build_room2_case_decision_template_formatted_html(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="PACIENTE",
    )

    assert body.startswith("<p>")
    assert "no. ocorrência: 12345" in body
    assert "paciente: PACIENTE" in body
    assert "decisao: aceitar" in body
    assert "suporte: nenhum" in body
    assert "motivo: (opcional)" in body
    assert f"caso: {case_id}" in body
    assert "<br>" in body
    assert body.endswith("</p>")


def test_build_room2_case_decision_template_message_uses_fallback_identification() -> None:
    case_id = UUID("44444444-4444-4444-4444-444444444444")

    body = build_room2_case_decision_template_message(
        case_id=case_id,
        agency_record_number=" ",
        patient_name=None,
    )

    assert body.startswith("no. ocorrência: não detectado\npaciente: não detectado\n")
    assert body.endswith(f"caso: {case_id}")


def test_build_room2_case_decision_template_formatted_html_uses_fallback_identification() -> None:
    case_id = UUID("44444444-4444-4444-4444-444444444444")

    body = build_room2_case_decision_template_formatted_html(
        case_id=case_id,
        agency_record_number=" ",
        patient_name=None,
    )

    assert "no. ocorrência: não detectado" in body
    assert "paciente: não detectado" in body
    assert f"caso: {case_id}" in body


def test_build_room2_case_summary_formatted_html_includes_sections() -> None:
    case_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    body = build_room2_case_summary_formatted_html(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="PACIENTE",
        structured_data={
            "policy_precheck": {
                "labs_pass": "yes",
                "ecg_present": "no",
                "labs_failed_items": ["INR ausente"],
            },
            "eda": {
                "labs": {"hb_g_dl": 10.2, "platelets_per_mm3": 140000, "inr": None},
                "ecg": {"report_present": "no", "abnormal_flag": "unknown"},
            },
        },
        summary_text="Resumo LLM1",
        suggested_action={"suggestion": "accept", "support_recommendation": "none"},
    )

    assert "<h1>Resumo técnico da triagem</h1>" in body
    assert "<h2>no. ocorrência: 12345</h2>" in body
    assert "<h2>paciente: PACIENTE</h2>" in body
    assert f"<p>caso: {case_id}</p>" not in body
    assert "<h2>Resumo clínico:</h2>" in body
    assert "<p>Resumo LLM1</p>" in body
    assert "<h2>Achados críticos:</h2>" in body
    assert "<h2>Pendências críticas:</h2>" in body
    assert "<h2>Decisão sugerida:</h2>" in body
    assert "<h2>Suporte recomendado:</h2>" in body
    assert "<h2>Motivo objetivo:</h2>" in body
    assert "<h2>Conduta sugerida:</h2>" not in body
    assert "<h2>Dados extraídos:</h2>" not in body
    assert "<h2>Recomendação do sistema:</h2>" not in body
    section_order = [
        "<h2>Resumo clínico:</h2>",
        "<h2>Achados críticos:</h2>",
        "<h2>Pendências críticas:</h2>",
        "<h2>Decisão sugerida:</h2>",
        "<h2>Suporte recomendado:</h2>",
        "<h2>Motivo objetivo:</h2>",
    ]
    section_positions = [body.index(section) for section in section_order]
    assert section_positions == sorted(section_positions)
    assert "<li>Hb: 10.2</li>" in body
    assert "<li>Plaquetas: 140000</li>" in body
    assert "<li>INR: não informado</li>" in body
    assert "<li>ECG presente: nao</li>" in body
    assert "<li>ECG sinal de alerta: indeterminado (sem evidência no laudo)</li>" in body
    assert "<li>Laboratório obrigatório (pré-check): sim</li>" in body
    assert "<li>ECG obrigatório (pré-check): nao</li>" in body
    assert "<li>Pendências de laboratório: INR ausente</li>" in body
    assert "prechecagem_politica:" not in body
    assert "ecg.sinal de alerta=" not in body
    assert "<li>aceitar</li>" in body


def test_build_room2_case_summary_message_removes_redundant_metadata() -> None:
    case_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

    body = build_room2_case_summary_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={
            "language": "pt-BR",
            "schema_version": "1.1",
            "agency_record_number": "12345",
            "patient": {"name": "JOSE"},
        },
        summary_text="Resumo clínico",
        suggested_action={
            "case_id": str(case_id),
            "language": "pt-BR",
            "schema_version": "1.1",
            "agency_record_number": "12345",
            "suggestion": "deny",
        },
    )

    assert "idioma:" not in body
    assert "versao_schema:" not in body
    assert "caso:" not in body
    assert body.count("no. ocorrência: 12345") == 1
    assert body.count("paciente: JOSE") == 1
    assert "numero_registro: 12345" not in body


def test_build_room2_case_summary_message_limits_clinical_summary_to_two_to_four_lines() -> None:
    case_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    summary_text = "Linha 1\nLinha 2\nLinha 3\nLinha 4\nLinha 5"

    body = build_room2_case_summary_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={},
        summary_text=summary_text,
        suggested_action={"suggestion": "accept", "support_recommendation": "none"},
    )

    lines = _extract_markdown_section_lines(
        body=body,
        section="## Resumo clínico:\n\n",
        next_section="\n\n## Achados críticos:",
    )
    assert 2 <= len(lines) <= 4
    assert "Linha 1" in lines
    assert "Linha 4" in lines
    assert "Linha 5" not in lines


def test_build_room2_case_summary_formatted_html_keeps_two_to_four_paragraphs_in_summary() -> None:
    case_id = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
    summary_text = "Resumo clínico curto para validação."

    body = build_room2_case_summary_formatted_html(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={},
        summary_text=summary_text,
        suggested_action={"suggestion": "accept", "support_recommendation": "none"},
    )

    start = body.index("<h2>Resumo clínico:</h2>") + len("<h2>Resumo clínico:</h2>")
    end = body.index("<h2>Achados críticos:</h2>", start)
    summary_chunk = body[start:end]

    paragraph_count = summary_chunk.count("<p>")
    assert 2 <= paragraph_count <= 4


def test_room2_summary_decision_and_support_come_only_from_suggested_action_markdown() -> None:
    case_id = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
    body = build_room2_case_summary_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={
            "suggestion": "accept",
            "support_recommendation": "none",
            "policy_precheck": {"labs_pass": "yes"},
        },
        summary_text="Resumo clínico base",
        suggested_action={
            "suggestion": "deny",
            "support_recommendation": "anesthesist_icu",
            "confidence": "media",
        },
    )

    decision_lines = _extract_markdown_section_lines(
        body=body,
        section="## Decisão sugerida:\n\n",
        next_section="\n\n## Suporte recomendado:",
    )
    support_lines = _extract_markdown_section_lines(
        body=body,
        section="## Suporte recomendado:\n\n",
        next_section="\n\n## Motivo objetivo:",
    )
    assert decision_lines == ["- negar"]
    assert support_lines == ["- anestesista_uti"]
    assert "aceitar" not in "\n".join(decision_lines + support_lines)


def test_room2_summary_decision_and_support_come_only_from_suggested_action_html() -> None:
    case_id = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
    body = build_room2_case_summary_formatted_html(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={
            "suggestion": "accept",
            "support_recommendation": "none",
        },
        summary_text="Resumo clínico base",
        suggested_action={
            "suggestion": "deny",
            "support_recommendation": "anesthesist",
        },
    )

    decision_chunk = _extract_html_section_chunk(
        body=body,
        section="<h2>Decisão sugerida:</h2>",
        next_section="<h2>Suporte recomendado:</h2>",
    )
    support_chunk = _extract_html_section_chunk(
        body=body,
        section="<h2>Suporte recomendado:</h2>",
        next_section="<h2>Motivo objetivo:</h2>",
    )

    assert "<li>negar</li>" in decision_chunk
    assert "<li>anestesista</li>" in support_chunk
    assert "aceitar" not in decision_chunk + support_chunk


def test_room2_summary_objective_reason_deny_ignores_short_rationale_text() -> None:
    case_id = UUID("12121212-1212-1212-1212-121212121212")
    reason_within_limit = (
        "Paciente com múltiplas comorbidades, necessidade de revisão laboratorial detalhada "
        "e rastreio pré-procedimento para reduzir risco perioperatório antes da endoscopia."
    )
    body = build_room2_case_summary_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={},
        summary_text="Resumo clínico base",
        suggested_action={
            "suggestion": "deny",
            "support_recommendation": "anesthesist_icu",
            "rationale": {"short_reason": reason_within_limit},
        },
    )

    reason_lines = _extract_markdown_section_lines(
        body=body,
        section="## Motivo objetivo:\n\n",
        next_section=None,
    )

    assert reason_lines == ["- Negado por: critérios mínimos de segurança não atendidos."]


def test_room2_summary_objective_reason_deny_ignores_long_rationale_text() -> None:
    case_id = UUID("23232323-2323-2323-2323-232323232323")
    long_reason = " ".join(["motivo" for _ in range(100)])

    body = build_room2_case_summary_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={},
        summary_text="Resumo clínico base",
        suggested_action={
            "suggestion": "deny",
            "support_recommendation": "anesthesist",
            "rationale": {"short_reason": long_reason},
        },
    )

    reason_lines = _extract_markdown_section_lines(
        body=body,
        section="## Motivo objetivo:\n\n",
        next_section=None,
    )

    assert reason_lines == ["- Negado por: critérios mínimos de segurança não atendidos."]


def test_room2_summary_critical_sections_use_nao_informado_fallback() -> None:
    case_id = UUID("abababab-abab-abab-abab-abababababab")
    body = build_room2_case_summary_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={},
        summary_text="Resumo clínico base",
        suggested_action={"suggestion": "accept", "support_recommendation": "none"},
    )

    findings_lines = _extract_markdown_section_lines(
        body=body,
        section="## Achados críticos:\n\n",
        next_section="\n\n## Pendências críticas:",
    )
    pending_lines = _extract_markdown_section_lines(
        body=body,
        section="## Pendências críticas:\n\n",
        next_section="\n\n## Decisão sugerida:",
    )

    assert findings_lines == [
        "- Hb: não informado",
        "- Plaquetas: não informado",
        "- INR: não informado",
        "- ECG presente: não informado",
        "- ECG sinal de alerta: não informado",
    ]
    assert pending_lines == [
        "- Laboratório obrigatório (pré-check): não informado",
        "- ECG obrigatório (pré-check): não informado",
        "- Pendências de laboratório: não informado",
    ]


def test_room2_summary_pending_precheck_unknown_uses_clear_text() -> None:
    case_id = UUID("cdcdcdcd-cdcd-cdcd-cdcd-cdcdcdcdcdcd")
    body = build_room2_case_summary_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={
            "policy_precheck": {
                "labs_pass": "unknown",
                "ecg_present": "unknown",
                "labs_failed_items": [],
            },
        },
        summary_text="Resumo clínico base",
        suggested_action={"suggestion": "accept", "support_recommendation": "none"},
    )

    pending_lines = _extract_markdown_section_lines(
        body=body,
        section="## Pendências críticas:\n\n",
        next_section="\n\n## Decisão sugerida:",
    )

    assert pending_lines == [
        "- Laboratório obrigatório (pré-check): indeterminado (sem evidência no laudo)",
        "- ECG obrigatório (pré-check): indeterminado (sem evidência no laudo)",
        "- Pendências de laboratório: indeterminadas (sem evidência no laudo)",
    ]


def test_room2_summary_findings_unknown_uses_indeterminado_label() -> None:
    case_id = UUID("efefefef-efef-efef-efef-efefefefefef")
    body = build_room2_case_summary_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={
            "eda": {
                "ecg": {
                    "report_present": "unknown",
                    "abnormal_flag": "unknown",
                },
            },
        },
        summary_text="Resumo clínico base",
        suggested_action={"suggestion": "accept", "support_recommendation": "none"},
    )

    findings_lines = _extract_markdown_section_lines(
        body=body,
        section="## Achados críticos:\n\n",
        next_section="\n\n## Pendências críticas:",
    )

    assert "- ECG presente: indeterminado" in findings_lines
    assert "- ECG sinal de alerta: indeterminado (sem evidência no laudo)" in findings_lines


def test_room2_summary_pending_precheck_unknown_uses_clear_text_in_html() -> None:
    case_id = UUID("dededede-dede-dede-dede-dededededede")
    body = build_room2_case_summary_formatted_html(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={
            "policy_precheck": {
                "labs_pass": "unknown",
                "ecg_present": "unknown",
                "labs_failed_items": [],
            },
        },
        summary_text="Resumo clínico base",
        suggested_action={"suggestion": "accept", "support_recommendation": "none"},
    )

    assert (
        "<li>Laboratório obrigatório (pré-check): indeterminado (sem evidência no laudo)</li>"
        in body
    )
    assert "<li>ECG obrigatório (pré-check): indeterminado (sem evidência no laudo)</li>" in body
    assert "<li>Pendências de laboratório: indeterminadas (sem evidência no laudo)</li>" in body


def test_room2_summary_clinical_validation_example_for_pending_section() -> None:
    case_id = UUID("f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0")
    body = build_room2_case_summary_message(
        case_id=case_id,
        agency_record_number="4809481",
        patient_name="VALDIRA GONCALVES DA SILVA REIS",
        structured_data={
            "eda": {
                "labs": {"hb_g_dl": None, "platelets_per_mm3": None, "inr": None},
                "ecg": {"report_present": "no", "abnormal_flag": "unknown"},
            },
            "policy_precheck": {
                "labs_pass": "unknown",
                "ecg_present": "no",
                "labs_failed_items": [],
            },
        },
        summary_text=(
            "Mulher de 64 anos com hematêmese e melena, dor epigástrica, "
            "encaminhada para EDA urgente."
        ),
        suggested_action={"suggestion": "deny", "support_recommendation": "anesthesist_icu"},
    )

    pending_lines = _extract_markdown_section_lines(
        body=body,
        section="## Pendências críticas:\n\n",
        next_section="\n\n## Decisão sugerida:",
    )

    assert pending_lines == [
        "- Laboratório obrigatório (pré-check): indeterminado (sem evidência no laudo)",
        "- ECG obrigatório (pré-check): nao",
        "- Pendências de laboratório: indeterminadas (sem evidência no laudo)",
    ]


def test_room2_summary_unknown_terms_do_not_render_as_desconhecido() -> None:
    case_id = UUID("f1f1f1f1-f1f1-f1f1-f1f1-f1f1f1f1f1f1")
    structured_data = {
        "eda": {
            "ecg": {
                "report_present": "unknown",
                "abnormal_flag": "unknown",
            },
        },
        "policy_precheck": {
            "labs_pass": "unknown",
            "ecg_present": "unknown",
            "labs_failed_items": [],
        },
    }

    markdown_body = build_room2_case_summary_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data=structured_data,
        summary_text="Resumo clínico base",
        suggested_action={"suggestion": "accept", "support_recommendation": "none"},
    )
    html_body = build_room2_case_summary_formatted_html(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data=structured_data,
        summary_text="Resumo clínico base",
        suggested_action={"suggestion": "accept", "support_recommendation": "none"},
    )

    assert "desconhecido" not in markdown_body
    assert "desconhecido" not in html_body
    assert "indeterminado" in markdown_body
    assert "indeterminado" in html_body


def test_room2_summary_includes_emergent_priority_phrase_for_bleeding_with_instability() -> None:
    case_id = UUID("56565656-5656-5656-5656-565656565656")
    body = build_room2_case_summary_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={
            "eda": {"indication_category": "bleeding"},
            "policy_precheck": {
                "notes": "Paciente com hipotensão importante e instabilidade hemodinâmica.",
            },
        },
        summary_text="Paciente com hematêmese e PA 79/53 em sala vermelha.",
        suggested_action={"suggestion": "accept", "support_recommendation": "anesthesist_icu"},
    )

    reason_lines = _extract_markdown_section_lines(
        body=body,
        section="## Motivo objetivo:\n\n",
        next_section=None,
    )
    assert any("PRIORIDADE EMERGENTE" in line for line in reason_lines)


def test_room2_summary_does_not_include_emergent_phrase_for_deny_even_with_instability() -> None:
    case_id = UUID("78777777-7877-7877-7877-787777777777")
    body = build_room2_case_summary_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={
            "eda": {"indication_category": "bleeding"},
            "policy_precheck": {
                "notes": "Instabilidade hemodinâmica documentada com hipotensão importante.",
            },
        },
        summary_text="Paciente com hematêmese e PA 78/50.",
        suggested_action={"suggestion": "deny", "support_recommendation": "none"},
    )

    reason_lines = _extract_markdown_section_lines(
        body=body,
        section="## Motivo objetivo:\n\n",
        next_section=None,
    )
    assert all("PRIORIDADE EMERGENTE" not in line for line in reason_lines)


def test_room2_summary_does_not_include_emergent_priority_phrase_without_instability() -> None:
    case_id = UUID("78787878-7878-7878-7878-787878787878")
    body = build_room2_case_summary_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={"eda": {"indication_category": "dyspepsia"}},
        summary_text="Paciente estável em investigação eletiva.",
        suggested_action={"suggestion": "accept", "support_recommendation": "none"},
    )

    reason_lines = _extract_markdown_section_lines(
        body=body,
        section="## Motivo objetivo:\n\n",
        next_section=None,
    )
    assert all("PRIORIDADE EMERGENTE" not in line for line in reason_lines)


def test_room2_summary_emergent_priority_phrase_html() -> None:
    case_id = UUID("79797979-7979-7979-7979-797979797979")
    body = build_room2_case_summary_formatted_html(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={
            "eda": {"indication_category": "bleeding"},
            "policy_precheck": {"notes": "Instabilidade hemodinâmica com hipotensão."},
        },
        summary_text="Paciente com hematêmese e PAS 82 em sala vermelha.",
        suggested_action={"suggestion": "accept", "support_recommendation": "anesthesist_icu"},
    )

    reason_chunk = _extract_html_section_chunk(
        body=body,
        section="<h2>Motivo objetivo:</h2>",
        next_section=None,
    )
    assert "PRIORIDADE EMERGENTE" in reason_chunk


def test_room2_summary_does_not_include_conduta_section_markdown_or_html() -> None:
    case_id = UUID("90909090-9090-9090-9090-909090909090")
    body = build_room2_case_summary_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={"eda": {"indication_category": "dyspepsia"}},
        summary_text="Caso estável, sem urgência imediata.",
        suggested_action={"suggestion": "accept", "support_recommendation": "none"},
    )
    formatted_body = build_room2_case_summary_formatted_html(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={"eda": {"indication_category": "dyspepsia"}},
        summary_text="Caso estável, sem urgência imediata.",
        suggested_action={"suggestion": "accept", "support_recommendation": "none"},
    )

    assert "## Conduta sugerida:" not in body
    assert "<h2>Conduta sugerida:</h2>" not in formatted_body


def test_room2_summary_objective_reason_accept_is_single_short_line_markdown() -> None:
    case_id = UUID("34343434-3434-3434-3434-343434343434")
    body = build_room2_case_summary_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={},
        summary_text="Resumo clínico base",
        suggested_action={
            "suggestion": "accept",
            "support_recommendation": "anesthesist",
            "rationale": {"short_reason": "Apto com suporte especializado."},
        },
    )

    reason_lines = _extract_markdown_section_lines(
        body=body,
        section="## Motivo objetivo:\n\n",
        next_section=None,
    )

    assert reason_lines == ["- Aceito com suporte de anestesista."]


def test_room2_summary_objective_reason_accept_is_single_short_line_html() -> None:
    case_id = UUID("35353535-3535-3535-3535-353535353535")
    body = build_room2_case_summary_formatted_html(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={},
        summary_text="Resumo clínico base",
        suggested_action={
            "suggestion": "accept",
            "support_recommendation": "anesthesist",
            "rationale": {"short_reason": "Apto com suporte especializado."},
        },
    )

    reason_chunk = _extract_html_section_chunk(
        body=body,
        section="<h2>Motivo objetivo:</h2>",
        next_section=None,
    )

    assert reason_chunk.count("<li>") == 1
    assert "Aceito com suporte de anestesista." in reason_chunk
    assert "Apto com suporte especializado." not in reason_chunk


def test_room2_summary_objective_reason_deny_never_mentions_acceptance_or_support() -> None:
    case_id = UUID("62626262-6262-6262-6262-626262626262")
    body = build_room2_case_summary_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={},
        summary_text="Resumo clínico base",
        suggested_action={
            "suggestion": "deny",
            "support_recommendation": "anesthesist",
            "rationale": {"short_reason": "Aceitar sem suporte por estabilidade."},
        },
    )

    reason_lines = _extract_markdown_section_lines(
        body=body,
        section="## Motivo objetivo:\n\n",
        next_section=None,
    )

    assert any(line.lower().startswith("- negado por:") for line in reason_lines)
    assert all("aceitar" not in line.lower() for line in reason_lines)
    assert all("suporte" not in line.lower() for line in reason_lines)


def test_room2_summary_objective_reason_deny_prioritizes_exclusion_cause() -> None:
    case_id = UUID("63636363-6363-6363-6363-636363636363")
    body = build_room2_case_summary_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={
            "policy_precheck": {
                "excluded_from_eda_flow": True,
                "exclusion_reason": "gastrostomia",
                "labs_required": True,
                "labs_pass": "no",
                "labs_failed_items": ["INR não informado"],
                "ecg_required": True,
                "ecg_present": "no",
            },
        },
        summary_text="Resumo clínico base",
        suggested_action={"suggestion": "deny", "support_recommendation": "none"},
    )

    reason_lines = _extract_markdown_section_lines(
        body=body,
        section="## Motivo objetivo:\n\n",
        next_section=None,
    )

    assert "fora do escopo eda" in " ".join(reason_lines).lower()


def test_room2_summary_objective_reason_deny_orders_labs_before_ecg() -> None:
    case_id = UUID("64646464-6464-6464-6464-646464646464")
    body = build_room2_case_summary_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={
            "policy_precheck": {
                "excluded_from_eda_flow": False,
                "labs_required": True,
                "labs_pass": "no",
                "labs_failed_items": ["INR não informado"],
                "ecg_required": True,
                "ecg_present": "no",
            },
        },
        summary_text="Resumo clínico base",
        suggested_action={"suggestion": "deny", "support_recommendation": "none"},
    )

    reason_text = " ".join(
        _extract_markdown_section_lines(
            body=body,
            section="## Motivo objetivo:\n\n",
            next_section=None,
        )
    ).lower()

    assert "pendência laboratorial obrigatória" in reason_text
    assert "ecg obrigatório ausente" in reason_text
    assert reason_text.index("pendência laboratorial obrigatória") < reason_text.index(
        "ecg obrigatório ausente"
    )


def test_room2_summary_objective_reason_deny_uses_ecg_cause_when_isolated() -> None:
    case_id = UUID("65656565-6565-6565-6565-656565656565")
    body = build_room2_case_summary_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={
            "policy_precheck": {
                "excluded_from_eda_flow": False,
                "labs_required": False,
                "labs_pass": "yes",
                "labs_failed_items": [],
                "ecg_required": True,
                "ecg_present": "no",
            },
        },
        summary_text="Resumo clínico base",
        suggested_action={"suggestion": "deny", "support_recommendation": "none"},
    )

    reason_text = " ".join(
        _extract_markdown_section_lines(
            body=body,
            section="## Motivo objetivo:\n\n",
            next_section=None,
        )
    ).lower()

    assert "ecg obrigatório ausente" in reason_text
    assert "pendência laboratorial obrigatória" not in reason_text
    assert "fora do escopo eda" not in reason_text


@pytest.mark.parametrize(
    ("reason_code", "expected_snippet"),
    [
        (
            "missing_ecg_with_cardiovascular_disease",
            "doença cardiovascular relatada sem laudo de ecg",
        ),
        (
            "missing_chest_xray_with_respiratory_risk",
            "risco respiratório relatado sem laudo de rx de tórax",
        ),
    ],
)
def test_room2_summary_objective_reason_deny_includes_missing_exam_context_from_preop_gate(
    reason_code: str,
    expected_snippet: str,
) -> None:
    case_id = UUID("65656565-6565-6565-6565-656565656565")
    suggested_action: dict[str, object] = {
        "suggestion": "deny",
        "support_recommendation": "none",
        "preop_gate": {
            "decision": "deny",
            "reason_code": reason_code,
            "reason_text": "negação determinística por exame ausente",
            "evidence_spans": [],
        },
    }
    body = build_room2_case_summary_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={
            "policy_precheck": {
                "excluded_from_eda_flow": False,
                "labs_required": False,
                "labs_pass": "yes",
                "labs_failed_items": [],
                "ecg_required": False,
                "ecg_present": "yes",
            },
        },
        summary_text="Resumo clínico base",
        suggested_action=suggested_action,
    )

    reason_text = " ".join(
        _extract_markdown_section_lines(
            body=body,
            section="## Motivo objetivo:\n\n",
            next_section=None,
        )
    ).lower()

    assert expected_snippet in reason_text
    assert "critérios mínimos de segurança não atendidos" not in reason_text

    formatted_body = build_room2_case_summary_formatted_html(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={
            "policy_precheck": {
                "excluded_from_eda_flow": False,
                "labs_required": False,
                "labs_pass": "yes",
                "labs_failed_items": [],
                "ecg_required": False,
                "ecg_present": "yes",
            },
        },
        summary_text="Resumo clínico base",
        suggested_action=suggested_action,
    )

    reason_chunk = _extract_html_section_chunk(
        body=formatted_body,
        section="<h2>Motivo objetivo:</h2>",
        next_section=None,
    ).lower()
    assert expected_snippet in reason_chunk


def test_room2_summary_objective_reason_deny_uses_fallback_when_no_known_cause() -> None:
    case_id = UUID("66666666-6666-6666-6666-666666666666")
    body = build_room2_case_summary_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={
            "policy_precheck": {
                "excluded_from_eda_flow": False,
                "labs_required": False,
                "labs_pass": "yes",
                "labs_failed_items": [],
                "ecg_required": False,
                "ecg_present": "yes",
            },
        },
        summary_text="Resumo clínico base",
        suggested_action={"suggestion": "deny", "support_recommendation": "none"},
    )

    reason_text = " ".join(
        _extract_markdown_section_lines(
            body=body,
            section="## Motivo objetivo:\n\n",
            next_section=None,
        )
    ).lower()

    assert "critérios mínimos de segurança não atendidos" in reason_text


def test_room2_summary_objective_reason_deny_limits_two_causes_with_marker() -> None:
    case_id = UUID("67676767-6767-6767-6767-676767676767")
    body = build_room2_case_summary_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={
            "policy_precheck": {
                "excluded_from_eda_flow": True,
                "exclusion_reason": "fora do escopo",
                "labs_required": True,
                "labs_pass": "no",
                "labs_failed_items": ["INR não informado"],
                "ecg_required": True,
                "ecg_present": "no",
            },
        },
        summary_text="Resumo clínico base",
        suggested_action={"suggestion": "deny", "support_recommendation": "none"},
    )

    reason_text = " ".join(
        _extract_markdown_section_lines(
            body=body,
            section="## Motivo objetivo:\n\n",
            next_section=None,
        )
    ).lower()

    assert "fora do escopo eda" in reason_text
    assert "pendência laboratorial obrigatória" in reason_text
    assert "e outras pendências críticas" in reason_text
    assert "ecg obrigatório ausente" not in reason_text


def test_room2_summary_deny_reason_consistent_between_markdown_and_html() -> None:
    case_id = UUID("69696969-6969-6969-6969-696969696969")
    structured_data: dict[str, object] = {
        "policy_precheck": {
            "excluded_from_eda_flow": True,
            "exclusion_reason": "fora do escopo",
            "labs_required": True,
            "labs_pass": "no",
            "labs_failed_items": ["INR não informado"],
            "ecg_required": True,
            "ecg_present": "no",
        },
    }
    suggested_action: dict[str, object] = {
        "suggestion": "deny",
        "support_recommendation": "none",
    }

    markdown_body = build_room2_case_summary_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data=structured_data,
        summary_text="Resumo clínico base",
        suggested_action=suggested_action,
    )
    html_body = build_room2_case_summary_formatted_html(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data=structured_data,
        summary_text="Resumo clínico base",
        suggested_action=suggested_action,
    )

    markdown_reason = " ".join(
        _extract_markdown_section_lines(
            body=markdown_body,
            section="## Motivo objetivo:\n\n",
            next_section=None,
        )
    )
    html_reason = _extract_html_section_chunk(
        body=html_body,
        section="<h2>Motivo objetivo:</h2>",
        next_section=None,
    )

    assert "Negado por: solicitação fora do escopo EDA (fora do escopo)" in markdown_reason
    assert "pendência laboratorial obrigatória (INR não informado)" in markdown_reason
    assert "e outras pendências críticas" in markdown_reason
    assert "PRIORIDADE EMERGENTE" not in markdown_reason

    assert "Negado por: solicitação fora do escopo EDA (fora do escopo)" in html_reason
    assert "pendência laboratorial obrigatória (INR não informado)" in html_reason
    assert "e outras pendências críticas" in html_reason
    assert "PRIORIDADE EMERGENTE" not in html_reason


def test_room2_summary_deny_ignores_conflicting_short_reason_when_cause_available() -> None:
    case_id = UUID("68686868-6868-6868-6868-686868686868")
    body = build_room2_case_summary_message(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="JOSE",
        structured_data={
            "policy_precheck": {
                "excluded_from_eda_flow": False,
                "labs_required": True,
                "labs_pass": "no",
                "labs_failed_items": ["INR não informado"],
                "ecg_required": False,
                "ecg_present": "yes",
            },
        },
        summary_text="Resumo clínico base",
        suggested_action={
            "suggestion": "deny",
            "support_recommendation": "none",
            "rationale": {"short_reason": "Aceitar sem suporte por estabilidade."},
        },
    )

    reason_text = " ".join(
        _extract_markdown_section_lines(
            body=body,
            section="## Motivo objetivo:\n\n",
            next_section=None,
        )
    ).lower()

    assert "pendência laboratorial obrigatória" in reason_text
    assert "aceitar sem suporte por estabilidade" not in reason_text


def test_build_room2_decision_ack_message_has_deterministic_success_fields() -> None:
    case_id = UUID("44444444-4444-4444-4444-444444444444")

    body = build_room2_decision_ack_message(
        case_id=case_id,
        decision="accept",
        support_flag="none",
        reason="criterios atendidos",
    )

    assert "resultado: sucesso" in body
    assert "no. ocorrência: não detectado" in body
    assert "paciente: não detectado" in body
    assert f"caso: {case_id}" not in body
    assert "decisao: aceitar" in body
    assert "suporte: nenhum" in body
    assert "motivo: criterios atendidos" in body


def test_build_room2_decision_error_message_has_actionable_guidance() -> None:
    case_id = UUID("55555555-5555-5555-5555-555555555555")

    body = build_room2_decision_error_message(
        case_id=case_id,
        error_code="invalid_template",
    )

    assert "resultado: erro" in body
    assert f"caso: {case_id}" in body
    assert "codigo_erro: invalid_template" in body
    assert "acao:" in body
    assert "Modelo obrigatório" in body
    assert "decisao: aceitar|negar" in body
