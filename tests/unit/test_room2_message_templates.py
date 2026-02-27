from __future__ import annotations

from uuid import UUID

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


def _extract_markdown_section_lines(*, body: str, section: str, next_section: str) -> list[str]:
    start = body.index(section) + len(section)
    end = body.index(next_section, start)
    chunk = body[start:end]
    return [line.strip() for line in chunk.splitlines() if line.strip()]


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
            "policy_precheck": {"labs_pass": "yes", "pediatric_flag": True},
            "eda": {"asa": {"class": "II"}, "ecg": {"abnormal_flag": "unknown"}},
        },
        summary_text="Resumo LLM1",
        suggested_action={"suggestion": "accept", "support_recommendation": "none"},
    )

    assert "no. ocorrência: 12345" in body
    assert "paciente: PACIENTE" in body
    assert f"caso: {case_id}" not in body
    assert "Resumo LLM1" in body
    assert "# Resumo técnico da triagem" in body
    assert "## Resumo clínico:" in body
    assert "## Achados críticos:" in body
    assert "## Pendências críticas:" in body
    assert "## Decisão sugerida:" in body
    assert "## Suporte recomendado:" in body
    assert "## Motivo objetivo:" in body
    assert "## Conduta sugerida:" in body
    section_order = [
        "## Resumo clínico:",
        "## Achados críticos:",
        "## Pendências críticas:",
        "## Decisão sugerida:",
        "## Suporte recomendado:",
        "## Motivo objetivo:",
        "## Conduta sugerida:",
    ]
    section_positions = [body.index(section) for section in section_order]
    assert section_positions == sorted(section_positions)
    assert "Consulte o relatório original para dados estruturados completos." in body
    assert "Resumo detalhado disponível no histórico técnico do caso." in body
    assert "flag_pediatrico" not in body
    assert "abnormal_flag" not in body
    assert "prechecagem_politica:" not in body
    assert "asa.classe=" not in body
    assert "ecg.sinal de alerta=" not in body
    assert "aceitar" in body
    assert "accept" not in body
    assert "Achados críticos" in body
    assert "Conduta sugerida" in body
    assert "```json" not in body


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

    body = build_room2_case_decision_template_message(case_id=case_id)

    assert body.startswith("decisao: aceitar\n")
    assert "suporte: nenhum\n" in body
    assert "motivo: (opcional)\n" in body
    assert body.endswith(f"caso: {case_id}")


def test_build_room2_case_decision_template_formatted_html_has_plain_lines() -> None:
    case_id = UUID("33333333-3333-3333-3333-333333333333")

    body = build_room2_case_decision_template_formatted_html(case_id=case_id)

    assert body.startswith("<p>")
    assert "decisao: aceitar" in body
    assert "suporte: nenhum" in body
    assert "motivo: (opcional)" in body
    assert f"caso: {case_id}" in body
    assert "<br>" in body
    assert body.endswith("</p>")


def test_build_room2_case_summary_formatted_html_includes_sections() -> None:
    case_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    body = build_room2_case_summary_formatted_html(
        case_id=case_id,
        agency_record_number="12345",
        patient_name="PACIENTE",
        structured_data={
            "policy_precheck": {"labs_pass": "yes", "pediatric_flag": True},
            "eda": {"ecg": {"abnormal_flag": "unknown"}},
        },
        summary_text="Resumo LLM1",
        suggested_action={"suggestion": "accept", "support_recommendation": "none"},
    )

    assert "<h1>Resumo técnico da triagem</h1>" in body
    assert "<p>no. ocorrência: 12345</p>" in body
    assert "<p>paciente: PACIENTE</p>" in body
    assert f"<p>caso: {case_id}</p>" not in body
    assert "<h2>Resumo clínico:</h2>" in body
    assert "<p>Resumo LLM1</p>" in body
    assert "<h2>Achados críticos:</h2>" in body
    assert "<h2>Pendências críticas:</h2>" in body
    assert "<h2>Decisão sugerida:</h2>" in body
    assert "<h2>Suporte recomendado:</h2>" in body
    assert "<h2>Motivo objetivo:</h2>" in body
    assert "<h2>Conduta sugerida:</h2>" in body
    section_order = [
        "<h2>Resumo clínico:</h2>",
        "<h2>Achados críticos:</h2>",
        "<h2>Pendências críticas:</h2>",
        "<h2>Decisão sugerida:</h2>",
        "<h2>Suporte recomendado:</h2>",
        "<h2>Motivo objetivo:</h2>",
        "<h2>Conduta sugerida:</h2>",
    ]
    section_positions = [body.index(section) for section in section_order]
    assert section_positions == sorted(section_positions)
    assert "<li>Consulte o relatório original para dados estruturados completos.</li>" in body
    assert "<li>Resumo detalhado disponível no histórico técnico do caso.</li>" in body
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
