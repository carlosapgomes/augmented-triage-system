"""Matrix message templates for triage workflow posts."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from html import escape
from uuid import UUID
from zoneinfo import ZoneInfo

# Case-id visibility contract across Room-1/2/3 builders:
# - structural: parser-bound templates must preserve `caso: <uuid>` line.
# - informational: UUID is not parser-critical and can be de-emphasized in UX copy.
STRUCTURAL_CASE_ID_TEMPLATE_BUILDERS: tuple[str, ...] = (
    "build_room2_case_decision_template_message",
    "build_room2_case_decision_template_formatted_html",
    "build_room2_decision_error_message",
    "build_room3_reply_template_message",
    "build_room3_invalid_format_reprompt",
)

INFORMATIONAL_CASE_ID_TEMPLATE_BUILDERS: tuple[str, ...] = (
    "build_room2_widget_message",
    "build_room2_case_pdf_message",
    "build_room2_case_pdf_formatted_html",
    "build_room2_case_pdf_attachment_filename",
    "build_room2_case_summary_message",
    "build_room2_case_summary_formatted_html",
    "build_room2_case_decision_instructions_message",
    "build_room2_case_decision_instructions_formatted_html",
    "build_room2_ack_message",
    "build_room2_decision_ack_message",
    "build_room3_request_message",
    "build_room3_ack_message",
    "build_room1_final_accepted_message",
    "build_room1_final_immediate_message",
    "build_room1_final_denied_triage_message",
    "build_room1_final_denied_appointment_message",
    "build_room1_final_failure_message",
    "build_room1_final_scope_manual_review_message",
)

_ROOM2_SUMMARY_BRT_ZONE = ZoneInfo("America/Bahia")


def build_human_identification_block(
    *,
    agency_record_number: str | None,
    patient_name: str | None,
) -> str:
    """Build standardized human-readable identification lines for case messages."""

    record_value = _normalize_human_identification_value(agency_record_number)
    patient_value = _normalize_human_identification_value(patient_name)
    return f"no. ocorrência: {record_value}\npaciente: {patient_value}"


def build_human_identification_heading_block(
    *,
    agency_record_number: str | None,
    patient_name: str | None,
) -> str:
    """Build identification lines as Markdown headings for first-contact messages."""

    record_value = _normalize_human_identification_value(agency_record_number)
    patient_value = _normalize_human_identification_value(patient_name)
    return f"## no. ocorrência: {record_value}\n## paciente: {patient_value}"


_PT_BR_KEY_MAP: dict[str, str] = {
    "agency_record_number": "numero_registro",
    "age": "idade",
    "asa": "asa",
    "bullet_points": "pontos",
    "cardiovascular_risk": "risco_cardiovascular",
    "case_id": "caso",
    "class": "classe",
    "confidence": "confianca",
    "details": "detalhes",
    "document_id": "documento",
    "ecg": "ecg",
    "abnormal_flag": "sinal de alerta",
    "ecg_ok": "ecg_ok",
    "ecg_present": "ecg_presente",
    "ecg_required": "ecg_obrigatorio",
    "eda": "eda",
    "excluded_from_eda_flow": "fora_fluxo_eda",
    "excluded_request": "solicitacao_excluida",
    "exclusion_reason": "motivo_exclusao",
    "exclusion_type": "tipo_exclusao",
    "extraction_quality": "qualidade_extracao",
    "foreign_body_suspected": "suspeita_corpo_estranho",
    "hb_g_dl": "hemoglobina_g_dl",
    "indication_category": "categoria_indicacao",
    "inr": "inr",
    "is_pediatric": "pediatrico",
    "labs": "laboratorio",
    "labs_failed_items": "itens_reprovados",
    "labs_ok": "laboratorio_ok",
    "labs_pass": "laboratorio_aprovado",
    "labs_required": "laboratorio_obrigatorio",
    "language": "idioma",
    "level": "nivel",
    "missing_fields": "campos_ausentes",
    "missing_info_questions": "perguntas_faltantes",
    "name": "nome",
    "notes": "notas",
    "one_liner": "uma_linha",
    "patient": "paciente",
    "pediatric_flag": "é pediátrico?",
    "platelets_per_mm3": "plaquetas_mm3",
    "policy_alignment": "alinhamento_politica",
    "policy_precheck": "prechecagem_politica",
    "rationale": "justificativa",
    "reason": "motivo",
    "report_present": "laudo_presente",
    "requested_procedure": "procedimento_solicitado",
    "schema_version": "versao_schema",
    "sex": "sexo",
    "short_reason": "motivo_curto",
    "source_text_hint": "fonte_texto",
    "suggestion": "sugestao",
    "support_recommendation": "recomendacao_suporte",
    "summary": "resumo_estruturado",
    "urgency": "urgencia",
}


def _normalize_human_identification_value(value: str | None) -> str:
    normalized = (value or "").strip()
    if not normalized:
        return "não detectado"
    return normalized


def _build_human_identification_html(
    *,
    agency_record_number: str | None,
    patient_name: str | None,
) -> str:
    record_value = _normalize_human_identification_value(agency_record_number)
    patient_value = _normalize_human_identification_value(patient_name)
    return (
        f"<p>no. ocorrência: {escape(record_value)}</p>"
        f"<p>paciente: {escape(patient_value)}</p>"
    )


def _build_human_identification_heading_html(
    *,
    agency_record_number: str | None,
    patient_name: str | None,
) -> str:
    record_value = _normalize_human_identification_value(agency_record_number)
    patient_value = _normalize_human_identification_value(patient_name)
    return (
        f"<h2>no. ocorrência: {escape(record_value)}</h2>"
        f"<h2>paciente: {escape(patient_value)}</h2>"
    )


def _build_human_identification_html_multiline(
    *,
    agency_record_number: str | None,
    patient_name: str | None,
) -> str:
    record_value = _normalize_human_identification_value(agency_record_number)
    patient_value = _normalize_human_identification_value(patient_name)
    return (
        "<p>"
        f"no. ocorrência: {escape(record_value)}<br>"
        f"paciente: {escape(patient_value)}"
        "</p>"
    )


def build_room2_widget_message(
    *,
    case_id: UUID,
    agency_record_number: str,
    patient_name: str | None = None,
    widget_launch_url: str,
    payload: dict[str, object],
) -> str:
    """Build Room-2 widget post body with embedded JSON payload."""

    payload_json = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    identification_block = build_human_identification_block(
        agency_record_number=agency_record_number,
        patient_name=patient_name,
    )
    return (
        "Solicitação de triagem\n"
        f"{identification_block}\n\n"
        f"Abra o widget de decisão: {widget_launch_url}\n\n"
        "Payload do widget:\n"
        f"```json\n{payload_json}\n```"
    )


def build_room2_case_pdf_message(
    *,
    case_id: UUID,
    agency_record_number: str,
    patient_name: str | None = None,
    extracted_text: str,
) -> str:
    """Build Room-2 message I body with concise context plus PDF attachment guidance."""
    _ = extracted_text

    identification_block = build_human_identification_block(
        agency_record_number=agency_record_number,
        patient_name=patient_name,
    )
    return (
        "# Solicitação de triagem - contexto original\n\n"
        f"{identification_block}\n\n"
        "O PDF original do relatório foi anexado como resposta a esta mensagem."
    )


def build_room2_case_pdf_formatted_html(
    *,
    case_id: UUID,
    agency_record_number: str,
    patient_name: str | None = None,
    extracted_text: str,
) -> str:
    """Build Room-2 message I HTML payload with concise PDF attachment guidance."""
    _ = extracted_text

    identification_html = _build_human_identification_html(
        agency_record_number=agency_record_number,
        patient_name=patient_name,
    )
    return (
        "<h1>Solicitação de triagem - contexto original</h1>"
        f"{identification_html}"
        "<p>O PDF original do relatório foi anexado como resposta a esta mensagem.</p>"
    )


def build_room2_case_pdf_attachment_filename(
    *,
    case_id: UUID,
    agency_record_number: str | None = None,
) -> str:
    """Build deterministic Room-2 original report PDF attachment filename."""

    record_slug = _normalize_record_number_for_filename(agency_record_number)
    return f"ocorrencia-{record_slug}-caso-{case_id}-relatorio-original.pdf"


def build_room2_case_summary_message(
    *,
    case_id: UUID,
    agency_record_number: str | None = None,
    patient_name: str | None = None,
    structured_data: dict[str, object],
    summary_text: str,
    suggested_action: dict[str, object],
    recent_denial_context: dict[str, object] | None = None,
) -> str:
    """Build Room-2 message II body using markdown-like section headings."""

    _ = case_id
    summary_lines = _build_room2_clinical_summary_lines(summary_text)
    summary_block = "\n".join(summary_lines)
    findings_block = "\n".join(_build_room2_critical_findings_lines(structured_data))
    pending_block = "\n".join(_build_room2_critical_pending_lines(structured_data))
    decision_block = "\n".join(_build_room2_decision_lines(suggested_action))
    support_block = "\n".join(_build_room2_support_lines(suggested_action))
    asa_block = "\n".join(
        _build_room2_asa_lines(
            suggested_action=suggested_action,
            structured_data=structured_data,
        )
    )
    reason_block = "\n".join(
        _build_room2_objective_reason_lines(
            suggested_action=suggested_action,
            structured_data=structured_data,
            summary_text=summary_text,
        )
    )
    recent_denial_block = _build_room2_recent_denial_markdown_block(recent_denial_context)
    identification_block = build_human_identification_heading_block(
        agency_record_number=agency_record_number,
        patient_name=patient_name,
    )
    context_block = _build_room2_case_context_markdown_block(structured_data)

    message = (
        "# Resumo técnico da triagem\n\n"
        f"{identification_block}\n\n"
        f"{context_block}\n\n"
        "## Resumo clínico:\n\n"
        f"{summary_block}\n\n"
        "## Achados críticos:\n\n"
        f"{findings_block}\n\n"
        "## Pendências críticas:\n\n"
        f"{pending_block}\n\n"
        "## Decisão sugerida:\n\n"
        f"{decision_block}\n\n"
        "## Suporte recomendado:\n\n"
        f"{support_block}\n\n"
        "## ASA estimado:\n\n"
        f"{asa_block}\n\n"
        "## Motivo objetivo:\n\n"
        f"{reason_block}"
    )
    if recent_denial_block is not None:
        message = f"{message}\n\n{recent_denial_block}"
    return message


def build_room2_case_summary_formatted_html(
    *,
    case_id: UUID,
    agency_record_number: str | None = None,
    patient_name: str | None = None,
    structured_data: dict[str, object],
    summary_text: str,
    suggested_action: dict[str, object],
    recent_denial_context: dict[str, object] | None = None,
) -> str:
    """Build Room-2 message II HTML payload for Matrix formatted_body rendering."""

    _ = case_id
    summary_html = _format_room2_clinical_summary_html(summary_text)
    findings_html = _format_markdown_lines_html(
        _build_room2_critical_findings_lines(structured_data)
    )
    pending_html = _format_markdown_lines_html(
        _build_room2_critical_pending_lines(structured_data)
    )
    decision_html = _format_markdown_lines_html(_build_room2_decision_lines(suggested_action))
    support_html = _format_markdown_lines_html(_build_room2_support_lines(suggested_action))
    asa_html = _format_markdown_lines_html(
        _build_room2_asa_lines(
            suggested_action=suggested_action,
            structured_data=structured_data,
        )
    )
    reason_html = _format_markdown_lines_html(
        _build_room2_objective_reason_lines(
            suggested_action=suggested_action,
            structured_data=structured_data,
            summary_text=summary_text,
        )
    )
    recent_denial_html = _build_room2_recent_denial_html_block(recent_denial_context)
    identification_html = _build_human_identification_heading_html(
        agency_record_number=agency_record_number,
        patient_name=patient_name,
    )
    context_html = _build_room2_case_context_html(structured_data)

    formatted = (
        "<h1>Resumo técnico da triagem</h1>"
        f"{identification_html}"
        f"{context_html}"
        "<h2>Resumo clínico:</h2>"
        f"{summary_html}"
        "<h2>Achados críticos:</h2>"
        f"{findings_html}"
        "<h2>Pendências críticas:</h2>"
        f"{pending_html}"
        "<h2>Decisão sugerida:</h2>"
        f"{decision_html}"
        "<h2>Suporte recomendado:</h2>"
        f"{support_html}"
        "<h2>ASA estimado:</h2>"
        f"{asa_html}"
        "<h2>Motivo objetivo:</h2>"
        f"{reason_html}"
    )
    if recent_denial_html is not None:
        formatted = f"{formatted}<h2>Histórico de negativa recente:</h2>{recent_denial_html}"
    return formatted


def _build_room2_case_context_markdown_block(structured_data: dict[str, object]) -> str:
    """Return compact context lines shown near Room-2 human identification area."""

    return "\n".join(_build_room2_case_context_lines(structured_data))



def _build_room2_case_context_html(structured_data: dict[str, object]) -> str:
    """Return HTML context paragraphs shown near Room-2 human identification area."""

    return "".join(
        f"<p>{escape(line)}</p>" for line in _build_room2_case_context_lines(structured_data)
    )


def _build_room2_origin_line(structured_data: dict[str, object]) -> str:
    """Build origin display line from structured origin_context data.

    Renders as ``origem: city (UF) - hospital - unit`` when data is available.
    UF, hospital, and unit are optional.  Returns fallback text when no
    meaningful origin data exists.
    """

    origin = _extract_room2_nested_value(structured_data, "origin_context")
    if not isinstance(origin, dict):
        return "origem: sem evidência no laudo"

    city = origin.get("city")
    hospital = origin.get("hospital")
    unit = origin.get("unit")
    state_uf = origin.get("state_uf")

    parts: list[str] = []

    city_str = _normalize_room2_origin_field(city)
    uf_str = _normalize_room2_origin_field(state_uf)

    if city_str:
        if uf_str:
            parts.append(f"{city_str} ({uf_str})")
        else:
            parts.append(city_str)

    hospital_str = _normalize_room2_origin_field(hospital)
    if hospital_str:
        parts.append(hospital_str)

    unit_str = _normalize_room2_origin_field(unit)
    if unit_str:
        parts.append(unit_str)

    if not parts:
        return "origem: sem evidência no laudo"
    return f"origem: {' - '.join(parts)}"


def _normalize_room2_origin_field(value: object) -> str:
    """Normalize origin field to non-empty string or empty string."""

    if isinstance(value, str):
        normalized = value.strip()
        if normalized:
            return normalized
    return ""


def _build_room2_transfusion_lines(structured_data: dict[str, object]) -> list[str]:
    """Build mandatory transfusion lines from structured transfusion data.

    Always renders the question line ``Há relato de transfusão? sim|não``.
    When the answer is ``sim``, appends total units and hemocomponent lines.
    Absence of transfusion data defaults to ``não``.
    """

    transfusion = _extract_room2_nested_value(structured_data, "transfusion")

    had_value = None
    if isinstance(transfusion, dict):
        had_value = transfusion.get("had_transfusion")

    is_yes = isinstance(had_value, str) and had_value.strip().lower() == "yes"

    lines: list[str] = [f"Há relato de transfusão? {'sim' if is_yes else 'não'}"]

    if is_yes and isinstance(transfusion, dict):
        total_units = transfusion.get("total_units")
        hemocomponent = transfusion.get("hemocomponent")

        units_label = (
            str(total_units) if isinstance(total_units, (int, float)) else "não informado"
        )
        hemo_label = (
            str(hemocomponent).strip()
            if isinstance(hemocomponent, str) and hemocomponent.strip()
            else "não informado"
        )
        lines.append(f"Total de unidades transfundidas: {units_label}")
        lines.append(f"Hemocomponente: {hemo_label}")

    return lines



def _build_room2_tracked_exam_lines(structured_data: dict[str, object]) -> list[str]:
    """Build tracked exam display lines with recency markers.

    Renders each tracked exam as ``label: value`` with an optional suffix:

    - ``(mais recente)`` when ``is_most_recent`` is ``True`` and a date is available.
    - ``(recência indeterminada (sem data no laudo))`` when ``is_most_recent``
      is ``True`` but no date exists.

    Tie-breaking: when multiple exams of the same type share the same datetime,
    the last textual occurrence (later in the list) is rendered as most recent.
    """

    tracked_exams = structured_data.get("tracked_exams")
    if not isinstance(tracked_exams, list) or not tracked_exams:
        return []

    lines: list[str] = []
    for exam in tracked_exams:
        if not isinstance(exam, dict):
            continue

        exam_label = exam.get("exam_label")
        result_value = exam.get("result_value")
        is_most_recent = exam.get("is_most_recent")
        exam_datetime = exam.get("exam_datetime_iso")

        label_str = (
            str(exam_label).strip()
            if isinstance(exam_label, str) and exam_label.strip()
            else "exame"
        )
        value_str = (
            str(result_value).strip()
            if isinstance(result_value, str) and result_value.strip()
            else "não informado"
        )

        line = f"{label_str}: {value_str}"

        if is_most_recent is True:
            if isinstance(exam_datetime, str) and exam_datetime.strip():
                line += " (mais recente)"
            else:
                line += " (recência indeterminada (sem data no laudo))"

        lines.append(line)

    return lines


def _build_room2_case_context_lines(structured_data: dict[str, object]) -> list[str]:
    """Build canonical procedure, origin, transfusion, tracked exam, and pediatric
    context lines for Room-2 summary.
    """

    lines = [
        f"procedimento solicitado: {_resolve_room2_canonical_procedure_name(structured_data)}"
    ]
    lines.append(_build_room2_origin_line(structured_data))
    lines.extend(_build_room2_transfusion_lines(structured_data))
    lines.extend(_build_room2_tracked_exam_lines(structured_data))
    if _is_room2_pediatric_case(structured_data):
        lines.append("paciente pediátrico: sim")
    return lines



def _resolve_room2_canonical_procedure_name(structured_data: dict[str, object]) -> str:
    """Resolve supported EDA subtype to canonical human-readable procedure text."""

    subtype = _extract_room2_supported_eda_subtype(structured_data)
    if subtype == "gastrostomy":
        return "EDA para gastrostomia"
    if subtype == "esophageal_dilation":
        return "EDA para dilatação esofágica"
    if subtype == "foreign_body":
        return "EDA para retirada de corpo estranho"
    return "EDA"



def _extract_room2_supported_eda_subtype(structured_data: dict[str, object]) -> str:
    """Extract normalized supported EDA subtype from structured payload."""

    requested_subtype = _extract_room2_nested_value(
        structured_data,
        "eda",
        "requested_procedure",
        "subtype",
    )
    if requested_subtype in {"standard", "gastrostomy", "esophageal_dilation", "foreign_body"}:
        return str(requested_subtype)

    rulebook_subtype = _extract_room2_nested_value(
        structured_data,
        "preop_screening",
        "rulebook_signals",
        "eda_subtype",
    )
    if rulebook_subtype in {"standard", "gastrostomy", "esophageal_dilation", "foreign_body"}:
        return str(rulebook_subtype)
    return "standard"



def _is_room2_pediatric_case(structured_data: dict[str, object]) -> bool:
    """Return True when structured context explicitly marks a pediatric case."""

    age = _extract_room2_nested_value(structured_data, "patient", "age")
    if isinstance(age, int) and not isinstance(age, bool):
        return age < 16

    is_pediatric = _extract_room2_nested_value(structured_data, "eda", "is_pediatric")
    return is_pediatric is True



def _build_room2_recent_denial_markdown_block(
    recent_denial_context: dict[str, object] | None,
) -> str | None:
    """Return optional markdown section for recent denial context in Room-2 summary."""

    if recent_denial_context is None:
        return None

    lines = _build_room2_recent_denial_lines(recent_denial_context)
    block_body = "\n".join(lines)
    return "## Histórico de negativa recente:\n\n" f"{block_body}"


def _build_room2_recent_denial_html_block(
    recent_denial_context: dict[str, object] | None,
) -> str | None:
    """Return optional HTML section body for recent denial context in Room-2 summary."""

    if recent_denial_context is None:
        return None

    lines = _build_room2_recent_denial_lines(recent_denial_context)
    return _format_markdown_lines_html(lines)


def _build_room2_recent_denial_lines(
    recent_denial_context: dict[str, object],
) -> list[str]:
    """Return deterministic lines describing latest recent denial context."""

    decision = recent_denial_context.get("decision")
    reason = recent_denial_context.get("reason")
    decided_at_value = recent_denial_context.get("decided_at")

    decision_label = _format_room2_recent_denial_decision(decision)
    reason_label = _format_room2_recent_denial_reason(reason)
    decided_at_label = _format_room2_recent_denial_decided_at(decided_at_value)

    lines = [
        f"- Tipo da negativa mais recente: {decision_label}.",
        f"- Motivo da negativa mais recente: {reason_label}",
        f"- Data/hora da negativa mais recente: {decided_at_label}",
    ]

    counter = recent_denial_context.get("prior_denial_count_7d")
    if isinstance(counter, int):
        lines.append(f"- Total de negativas nos últimos 7 dias: {counter}")

    return lines


def _format_room2_recent_denial_decision(value: object) -> str:
    """Map internal prior decision enum to concise Room-2 display label."""

    if value == "deny_triage":
        return "negado na triagem"
    if value == "deny_appointment":
        return "negado no agendamento"
    return "negado"


def _format_room2_recent_denial_reason(value: object) -> str:
    """Normalize recent denial reason display with deterministic fallback."""

    if isinstance(value, str):
        normalized = value.strip()
        if normalized:
            return normalized
    return "não informado"


def _format_room2_recent_denial_decided_at(value: object) -> str:
    """Format recent denial timestamp for Room-2 summary block in BRT."""

    parsed = _parse_room2_recent_denial_datetime(value)
    if parsed is None:
        return "não informado"

    localized = parsed.astimezone(_ROOM2_SUMMARY_BRT_ZONE)
    return f"{localized.strftime('%d/%m/%Y %H:%M')} BRT"


def _parse_room2_recent_denial_datetime(value: object) -> datetime | None:
    """Parse recent denial datetime from typed or ISO-like values."""

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None

        iso_candidate = normalized
        if iso_candidate.endswith("Z"):
            iso_candidate = f"{iso_candidate[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(iso_candidate)
        except ValueError:
            return None

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed

    return None


def _build_room2_clinical_summary_lines(summary_text: str) -> list[str]:
    """Normalize clinical summary into a deterministic concise 2-4 line block."""

    stripped_lines = [line.strip() for line in summary_text.splitlines() if line.strip()]
    if not stripped_lines:
        return [
            "Resumo clínico não informado.",
            "Consulte o relatório original para contexto clínico.",
        ]

    if len(stripped_lines) >= 2:
        return stripped_lines[:4]

    one_liner = stripped_lines[0]
    words = one_liner.split()
    if len(words) >= 4:
        midpoint = len(words) // 2
        first_half = " ".join(words[:midpoint]).strip()
        second_half = " ".join(words[midpoint:]).strip()
        if first_half and second_half:
            return [first_half, second_half]

    return [
        one_liner,
        f"Base clínica: {one_liner}",
    ]


def _format_room2_clinical_summary_html(summary_text: str) -> str:
    """Render normalized clinical summary lines as HTML paragraphs."""

    lines = _build_room2_clinical_summary_lines(summary_text)
    return "".join(f"<p>{escape(line)}</p>" for line in lines)


def _build_room2_critical_findings_lines(structured_data: dict[str, object]) -> list[str]:
    """Return concise critical findings section lines."""

    hb_value = _extract_room2_nested_value(structured_data, "eda", "labs", "hb_g_dl")
    platelets_value = _extract_room2_nested_value(
        structured_data,
        "eda",
        "labs",
        "platelets_per_mm3",
    )
    inr_value = _extract_room2_nested_value(structured_data, "eda", "labs", "inr")
    ecg_present_value = _extract_room2_nested_value(
        structured_data,
        "eda",
        "ecg",
        "report_present",
    )
    ecg_alert_value = _extract_room2_nested_value(
        structured_data,
        "eda",
        "ecg",
        "abnormal_flag",
    )
    return [
        f"- Hb: {_format_room2_value_or_fallback(hb_value)}",
        f"- Plaquetas: {_format_room2_value_or_fallback(platelets_value)}",
        f"- INR: {_format_room2_value_or_fallback(inr_value)}",
        f"- ECG presente: {_format_room2_value_or_fallback(ecg_present_value)}",
        f"- ECG sinal de alerta: {_format_room2_unknown_value_with_evidence(ecg_alert_value)}",
    ]


def _build_room2_critical_pending_lines(structured_data: dict[str, object]) -> list[str]:
    """Return concise critical pending section lines."""

    precheck_labs_pass = _extract_room2_nested_value(
        structured_data,
        "policy_precheck",
        "labs_pass",
    )
    precheck_ecg_present = _extract_room2_nested_value(
        structured_data,
        "policy_precheck",
        "ecg_present",
    )
    labs_failed_items = _extract_room2_nested_value(
        structured_data,
        "policy_precheck",
        "labs_failed_items",
    )

    failed_items_text = "não informado"
    if isinstance(labs_failed_items, list):
        normalized_items = [str(item).strip() for item in labs_failed_items if str(item).strip()]
        if normalized_items:
            failed_items_text = ", ".join(normalized_items)
        elif _is_room2_unknown_precheck_value(precheck_labs_pass):
            failed_items_text = "indeterminadas (sem evidência no laudo)"

    lab_status = _format_room2_unknown_value_with_evidence(precheck_labs_pass)
    ecg_status = _format_room2_unknown_value_with_evidence(precheck_ecg_present)

    return [
        f"- Laboratório obrigatório (pré-check): {lab_status}",
        f"- ECG obrigatório (pré-check): {ecg_status}",
        f"- Pendências de laboratório: {failed_items_text}",
    ]


def _build_room2_decision_lines(
    suggested_action: dict[str, object],
) -> list[str]:
    """Return decision section lines based on reconciled suggestion payload."""

    suggestion = suggested_action.get("suggestion")
    if isinstance(suggestion, str):
        return [f"- {_format_scalar(suggestion)}"]
    return ["- não informado"]


def _build_room2_support_lines(suggested_action: dict[str, object]) -> list[str]:
    """Return support section lines based on reconciled suggestion payload."""

    support_recommendation = suggested_action.get("support_recommendation")
    if isinstance(support_recommendation, str):
        return [f"- {_format_scalar(support_recommendation)}"]
    return ["- não informado"]



def _build_room2_asa_lines(
    *,
    suggested_action: dict[str, object],
    structured_data: dict[str, object],
) -> list[str]:
    """Return practical ASA section lines from recommendation context or structured data."""

    asa_payload = suggested_action.get("asa")
    if isinstance(asa_payload, dict):
        display_text = asa_payload.get("display_text")
        if isinstance(display_text, str) and display_text.strip():
            return [f"- {display_text.strip()}"]

        bucket = asa_payload.get("bucket")
        if isinstance(bucket, str) and bucket.strip():
            return [f"- {_format_room2_asa_bucket(bucket.strip())}"]

    structured_asa = _extract_room2_nested_value(structured_data, "eda", "asa", "bucket")
    if isinstance(structured_asa, str) and structured_asa.strip():
        return [f"- {_format_room2_asa_bucket(structured_asa.strip())}"]

    return ["- não informado"]



def _format_room2_asa_bucket(value: str) -> str:
    """Map persisted ASA bucket to Room-2 human-readable display text."""

    if value == "insufficient_data":
        return "não foi possível estimar com os dados apresentados"
    return _map_presentation_value(value)



def _build_room2_objective_reason_lines(
    *,
    suggested_action: dict[str, object],
    structured_data: dict[str, object],
    summary_text: str,
) -> list[str]:
    """Return objective reason section lines aligned with decision and urgency context."""

    decision = suggested_action.get("suggestion")
    support_recommendation = suggested_action.get("support_recommendation")
    decision_label = _format_scalar(decision) if isinstance(decision, str) else "não informado"
    support_label = (
        _format_scalar(support_recommendation)
        if isinstance(support_recommendation, str)
        else "não informado"
    )

    include_emergent_phrase = _should_include_room2_emergent_priority_phrase(
        structured_data=structured_data,
        summary_text=summary_text,
    )
    reason = _extract_room2_short_reason(suggested_action)

    decision_key = decision.strip().lower() if isinstance(decision, str) else ""
    if decision_key == "deny":
        return _build_room2_objective_reason_deny_lines(
            structured_data=structured_data,
            suggested_action=suggested_action,
        )
    if decision_key == "accept":
        return _build_room2_objective_reason_accept_lines(
            decision_label=decision_label,
            support_label=support_label,
            include_emergent_phrase=include_emergent_phrase,
            reason=reason,
        )
    return _build_room2_objective_reason_unknown_decision_lines(
        decision_label=decision_label,
        support_label=support_label,
        include_emergent_phrase=include_emergent_phrase,
        reason=reason,
    )


def _build_room2_objective_reason_deny_lines(
    *,
    structured_data: dict[str, object],
    suggested_action: dict[str, object],
) -> list[str]:
    """Build objective reason lines for deny suggestion branch."""

    causes = _build_room2_objective_deny_causes(
        structured_data=structured_data,
        suggested_action=suggested_action,
    )
    visible_causes = causes[:2]
    cause_text = "; ".join(visible_causes)
    if len(causes) > 2:
        cause_text = f"{cause_text}; e outras pendências críticas"

    return [f"- Negado por: {cause_text}."]


def _build_room2_objective_deny_causes(
    *,
    structured_data: dict[str, object],
    suggested_action: dict[str, object],
) -> list[str]:
    """Return ordered deny causes derived from deterministic precheck signals."""

    preop_gate_cause = _map_room2_preop_reason_code_to_deny_cause(
        reason_code=_extract_room2_preop_gate_reason_code(
            suggested_action=suggested_action,
        ),
        reason_text=_extract_room2_preop_gate_reason_text(
            suggested_action=suggested_action,
        ),
    )
    if preop_gate_cause is not None:
        return [preop_gate_cause]

    causes: list[str] = []

    excluded_from_flow = _extract_room2_nested_value(
        structured_data,
        "policy_precheck",
        "excluded_from_eda_flow",
    )
    excluded_request = _extract_room2_nested_value(
        suggested_action,
        "policy_alignment",
        "excluded_request",
    )
    if excluded_from_flow is True or excluded_request is True:
        exclusion_reason = _extract_room2_nested_value(
            structured_data,
            "policy_precheck",
            "exclusion_reason",
        )
        if isinstance(exclusion_reason, str) and exclusion_reason.strip():
            causes.append(
                f"solicitação fora do escopo EDA ({' '.join(exclusion_reason.split())})",
            )
        else:
            causes.append("solicitação fora do escopo EDA")

    labs_required = _extract_room2_nested_value(structured_data, "policy_precheck", "labs_required")
    labs_pass = _extract_room2_nested_value(structured_data, "policy_precheck", "labs_pass")
    if labs_required is True and not _is_room2_yes_precheck_value(labs_pass):
        failed_items = _extract_room2_nested_value(
            structured_data,
            "policy_precheck",
            "labs_failed_items",
        )
        if isinstance(failed_items, list):
            normalized_items = [str(item).strip() for item in failed_items if str(item).strip()]
            if normalized_items:
                causes.append(
                    "pendência laboratorial obrigatória "
                    f"({', '.join(normalized_items)})",
                )
            else:
                causes.append("pendência laboratorial obrigatória")
        else:
            causes.append("pendência laboratorial obrigatória")

    ecg_required = _extract_room2_nested_value(structured_data, "policy_precheck", "ecg_required")
    ecg_present = _extract_room2_nested_value(structured_data, "policy_precheck", "ecg_present")
    if ecg_required is True and not _is_room2_yes_precheck_value(ecg_present):
        causes.append("ECG obrigatório ausente")

    if not causes:
        causes.append("critérios mínimos de segurança não atendidos")

    return causes


def _extract_room2_preop_gate_reason_code(*, suggested_action: dict[str, object]) -> str | None:
    """Extract deterministic preop gate reason-code from suggested action payload."""

    preop_gate = suggested_action.get("preop_gate")
    if isinstance(preop_gate, dict):
        preop_reason_code = preop_gate.get("reason_code")
        if isinstance(preop_reason_code, str):
            normalized = preop_reason_code.strip().lower()
            if normalized:
                return normalized

    reason_code = suggested_action.get("reason_code")
    if isinstance(reason_code, str):
        normalized = reason_code.strip().lower()
        if normalized:
            return normalized

    return None



def _extract_room2_preop_gate_reason_text(*, suggested_action: dict[str, object]) -> str | None:
    """Extract deterministic preop gate reason-text from suggested action payload."""

    preop_gate = suggested_action.get("preop_gate")
    if isinstance(preop_gate, dict):
        preop_reason_text = preop_gate.get("reason_text")
        if isinstance(preop_reason_text, str):
            normalized = " ".join(preop_reason_text.split())
            if normalized:
                return normalized

    reason_text = suggested_action.get("reason_text")
    if isinstance(reason_text, str):
        normalized = " ".join(reason_text.split())
        if normalized:
            return normalized

    return None



def _map_room2_preop_reason_code_to_deny_cause(
    *,
    reason_code: str | None,
    reason_text: str | None,
) -> str | None:
    """Map deterministic preop reason metadata to concise Room-2 deny explanation."""

    minimum_exam_labels = {
        "missing_minimum_exam_hb_or_ht": "Hb/Ht",
        "missing_minimum_exam_platelets": "plaquetas",
        "missing_minimum_exam_tp_inr_rni": "TP/INR/RNI",
        "missing_minimum_exam_ttpa": "TTPa",
        "missing_minimum_exam_urea": "ureia",
        "missing_minimum_exam_creatinine": "creatinina",
    }
    if reason_code in minimum_exam_labels:
        return f"exame mínimo obrigatório ausente: {minimum_exam_labels[reason_code]}"

    if reason_code == "missing_ecg_with_cardiovascular_disease":
        return "critério cardiovascular sem laudo mínimo de ECG"
    if reason_code == "missing_chest_xray_with_respiratory_risk":
        return "critério respiratório sem laudo mínimo de RX de tórax"
    if reason_code == "missing_echocardiogram_with_structural_heart_risk":
        return "critério cardíaco estrutural sem laudo mínimo de ecocardiograma"

    if reason_code in {"hb_below_threshold", "platelets_below_threshold", "inr_above_threshold"}:
        summarized_threshold = _summarize_room2_threshold_reason(reason_text)
        if summarized_threshold is not None:
            return f"contraindicação: {summarized_threshold}"
        return "contraindicação por limiar clínico excedido"
    return None



def _summarize_room2_threshold_reason(reason_text: str | None) -> str | None:
    """Collapse deterministic threshold reason text into concise Room-2 wording."""

    if reason_text is None:
        return None

    normalized = reason_text.split(" Sinalização pediátrica:", 1)[0].strip()
    normalized = normalized.removesuffix(".")
    normalized = normalized.replace(" do rulebook EDA", "")
    normalized = " ".join(normalized.split())
    if not normalized:
        return None
    return normalized


def _is_room2_yes_precheck_value(value: object) -> bool:
    """Return True when precheck enum-like value explicitly means yes."""

    return isinstance(value, str) and value.strip().lower() == "yes"


def _is_room2_unknown_precheck_value(value: object) -> bool:
    """Return True when precheck enum-like value explicitly means unknown."""

    return isinstance(value, str) and value.strip().lower() == "unknown"


def _build_room2_objective_reason_accept_lines(
    *,
    decision_label: str,
    support_label: str,
    include_emergent_phrase: bool,
    reason: str | None,
) -> list[str]:
    """Build objective reason lines for accept suggestion branch."""

    _ = decision_label, reason
    first_line = "- Aceito com suporte a definir."
    if support_label == "nenhum":
        first_line = "- Aceito sem suporte adicional."
    elif support_label in {"anestesista", "anestesista_uti"}:
        first_line = f"- Aceito com suporte de {support_label}."

    lines = [first_line]
    if include_emergent_phrase:
        lines.append(
            (
                "- PRIORIDADE EMERGENTE: estabilizar hemodinamicamente e seguir via "
                "urgente sem atraso por pendências não críticas."
            ),
        )
    return lines


def _build_room2_objective_reason_unknown_decision_lines(
    *,
    decision_label: str,
    support_label: str,
    include_emergent_phrase: bool,
    reason: str | None,
) -> list[str]:
    """Build objective reason lines for missing or unknown suggestion branch."""

    return _build_room2_objective_reason_default_lines(
        decision_label=decision_label,
        support_label=support_label,
        include_emergent_phrase=include_emergent_phrase,
        reason=reason,
    )


def _build_room2_objective_reason_default_lines(
    *,
    decision_label: str,
    support_label: str,
    include_emergent_phrase: bool,
    reason: str | None,
) -> list[str]:
    """Build legacy objective reason lines shared across decision branches."""

    lines = [f"- Decisão {decision_label} com suporte {support_label}."]
    if include_emergent_phrase:
        lines.append(
            (
                "- PRIORIDADE EMERGENTE: estabilizar hemodinamicamente e seguir via "
                "urgente sem atraso por pendências não críticas."
            ),
        )

    if reason:
        lines.append(f"- {_truncate_room2_reason_line(reason)}")
    return lines


def _extract_room2_short_reason(suggested_action: dict[str, object]) -> str | None:
    """Extract preferred short rationale text from reconciled suggestion payload."""

    rationale = suggested_action.get("rationale")
    if isinstance(rationale, str):
        normalized = rationale.strip()
        if normalized:
            return normalized
        return None
    if isinstance(rationale, dict):
        short_reason = rationale.get("short_reason")
        if isinstance(short_reason, str):
            normalized = short_reason.strip()
            if normalized:
                return normalized
    return None


def _truncate_room2_reason_line(reason: str, limit: int = 360) -> str:
    """Return normalized one-line reason text with protection cap for long rationale."""

    normalized = " ".join(reason.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 1].rstrip()}…"


def _should_include_room2_emergent_priority_phrase(
    *,
    structured_data: dict[str, object],
    summary_text: str,
) -> bool:
    """Return True when case indicates bleeding with documented hemodynamic instability."""

    return _is_room2_bleeding_case(
        structured_data=structured_data,
        summary_text=summary_text,
    ) and _has_room2_documented_hemodynamic_instability(
        structured_data=structured_data,
        summary_text=summary_text,
    )


def _is_room2_bleeding_case(*, structured_data: dict[str, object], summary_text: str) -> bool:
    """Detect bleeding context by structured indicator or narrative keywords."""

    indication_category = _extract_room2_nested_value(structured_data, "eda", "indication_category")
    if isinstance(indication_category, str) and indication_category.strip().lower() == "bleeding":
        return True

    combined_text = " ".join(_collect_room2_context_texts(structured_data, summary_text)).lower()
    bleeding_markers = ("hematêmese", "hematemese", "melena", "hda", "hemorragia digestiva")
    return any(marker in combined_text for marker in bleeding_markers)


def _has_room2_documented_hemodynamic_instability(
    *,
    structured_data: dict[str, object],
    summary_text: str,
) -> bool:
    """Detect documented hemodynamic instability by keywords or low systolic values."""

    texts = _collect_room2_context_texts(structured_data, summary_text)
    combined_text = " ".join(texts).lower()
    keyword_markers = (
        "instabilidade hemodin",
        "hemodinamicamente inst",
        "choque",
        "hipotensão",
        "hipotensao",
        "hipovol",
    )
    if any(marker in combined_text for marker in keyword_markers):
        return True

    systolic_values = _extract_room2_systolic_values(combined_text)
    return any(value < 90 for value in systolic_values)


def _collect_room2_context_texts(
    structured_data: dict[str, object],
    summary_text: str,
) -> list[str]:
    """Collect free-text fields relevant for emergent-context detection."""

    texts: list[str] = []
    if summary_text.strip():
        texts.append(summary_text.strip())

    policy_notes = _extract_room2_nested_value(structured_data, "policy_precheck", "notes")
    if isinstance(policy_notes, str) and policy_notes.strip():
        texts.append(policy_notes.strip())

    return texts


def _extract_room2_systolic_values(text: str) -> list[int]:
    """Extract systolic blood-pressure values from common textual notations."""

    values: list[int] = []
    single_patterns = (
        r"\bpas\s*[:=]?\s*([0-9]{2,3})\b",
    )
    paired_patterns = (
        r"\bpa\s*[:=]?\s*([0-9]{2,3})\s*[x/]\s*([0-9]{2,3})\b",
        r"\bta\s*[:=]?\s*([0-9]{2,3})\s*[x/]\s*([0-9]{2,3})\b",
    )

    for pattern in single_patterns:
        for match in re.finditer(pattern, text):
            values.append(int(match.group(1)))

    for pattern in paired_patterns:
        for match in re.finditer(pattern, text):
            values.append(int(match.group(1)))

    return values


def _extract_room2_nested_value(payload: dict[str, object], *keys: str) -> object | None:
    """Return nested dictionary value by key path, or None when missing."""

    current: object = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _format_room2_value_or_fallback(value: object | None) -> str:
    """Return human-readable scalar value with deterministic 'não informado' fallback."""

    if value is None:
        return "não informado"
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return "não informado"
        return _map_presentation_value(normalized)
    if isinstance(value, bool):
        return "sim" if value else "nao"
    if isinstance(value, (int, float)):
        return str(value)
    return str(value)


def _format_room2_unknown_value_with_evidence(value: object | None) -> str:
    """Return clearer wording when scalar value is unknown in source evidence."""

    formatted = _format_room2_value_or_fallback(value)
    if formatted in {"desconhecido", "indeterminado"}:
        return "indeterminado (sem evidência no laudo)"
    return formatted


def _translate_keys_to_portuguese(*, value: object) -> object:
    if isinstance(value, dict):
        translated: dict[str, object] = {}
        for key, nested in value.items():
            source_key = str(key)
            translated_key = _PT_BR_KEY_MAP.get(source_key, source_key)
            translated[translated_key] = _translate_keys_to_portuguese(value=nested)
        return translated
    if isinstance(value, list):
        return [_translate_keys_to_portuguese(value=item) for item in value]
    return value


def _format_markdown_lines(value: object) -> list[str]:
    if not isinstance(value, dict):
        return [f"- {_format_scalar(value)}"]

    top_level: dict[str, object] = {str(k): v for k, v in value.items()}
    if not top_level:
        return ["- (vazio)"]

    lines: list[str] = []
    for top_key in sorted(top_level):
        top_value = top_level[top_key]
        if isinstance(top_value, dict):
            lines.append(f"### {top_key}:")
            second_level: dict[str, object] = {str(k): v for k, v in top_value.items()}
            if not second_level:
                lines.append("- (vazio)")
                continue
            for second_key in sorted(second_level):
                second_value = second_level[second_key]
                lines.append(f"- {second_key}: {_format_compact_value(second_value)}")
            continue
        lines.append(f"- {top_key}: {_format_compact_value(top_value)}")
    return lines


def _format_compact_markdown_lines(value: object) -> list[str]:
    """Format dict payload using compact one-line-per-section representation."""

    if not isinstance(value, dict):
        return [f"- {_format_scalar(value)}"]

    top_level: dict[str, object] = {str(k): v for k, v in value.items()}
    if not top_level:
        return ["- (vazio)"]

    lines: list[str] = []
    for top_key in sorted(top_level):
        top_value = top_level[top_key]
        if isinstance(top_value, dict):
            flat_parts = _flatten_dict_pairs(top_value)
            if not flat_parts:
                lines.append(f"- {top_key}: (vazio)")
                continue
            lines.append(f"- {top_key}: {'; '.join(flat_parts)}")
            continue
        lines.append(f"- {top_key}: {_format_compact_value(top_value)}")
    return lines


def _format_paragraphs_html(value: str) -> str:
    stripped_lines = [line.strip() for line in value.splitlines() if line.strip()]
    if not stripped_lines:
        return "<p>(vazio)</p>"
    return "".join(f"<p>{escape(line)}</p>" for line in stripped_lines)


def _format_markdown_lines_html(lines: list[str]) -> str:
    html_parts: list[str] = []
    in_list = False

    for line in lines:
        content = line.strip()
        if not content:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            continue

        if content.startswith("### "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(f"<h3>{escape(content[4:])}</h3>")
            continue

        if content.startswith("- "):
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            html_parts.append(f"<li>{escape(content[2:])}</li>")
            continue

        if in_list:
            html_parts.append("</ul>")
            in_list = False
        html_parts.append(f"<p>{escape(content)}</p>")

    if in_list:
        html_parts.append("</ul>")

    if not html_parts:
        return "<p>(vazio)</p>"
    return "".join(html_parts)


def _format_compact_value(value: object) -> str:
    if isinstance(value, dict):
        nested: dict[str, object] = {str(k): v for k, v in value.items()}
        if not nested:
            return "(vazio)"
        parts = [f"{key}={_format_compact_value(nested[key])}" for key in sorted(nested)]
        return "; ".join(parts)
    if isinstance(value, list):
        if not value:
            return "(vazio)"
        return ", ".join(_format_compact_value(item) for item in value)
    return _format_scalar(value)


def _format_scalar(value: object) -> str:
    if value is None:
        return "(vazio)"
    if isinstance(value, bool):
        return "sim" if value else "nao"
    if isinstance(value, str):
        if not value:
            return "(vazio)"
        return _map_presentation_value(value)
    return str(value)


def _flatten_dict_pairs(value: dict[str, object], prefix: str = "") -> list[str]:
    """Flatten nested dict into key path pairs preserving all leaf values."""

    if not value:
        return []

    pairs: list[str] = []
    for key in sorted(value):
        nested = value[key]
        key_path = f"{prefix}.{key}" if prefix else key
        if isinstance(nested, dict):
            nested_pairs = _flatten_dict_pairs(
                {str(inner_key): inner_value for inner_key, inner_value in nested.items()},
                prefix=key_path,
            )
            if nested_pairs:
                pairs.extend(nested_pairs)
                continue
            pairs.append(f"{key_path}=(vazio)")
            continue
        pairs.append(f"{key_path}={_format_compact_value(nested)}")
    return pairs


def _prune_redundant_summary_fields(
    *,
    structured_data: object,
    suggested_action: object,
) -> tuple[object, object]:
    """Remove redundant metadata fields to reduce vertical payload size."""

    if not isinstance(structured_data, dict) or not isinstance(suggested_action, dict):
        return structured_data, suggested_action

    shared_drop_keys = {"idioma", "versao_schema"}
    structured_clean = {
        str(key): value
        for key, value in structured_data.items()
        if str(key) not in shared_drop_keys
    }
    suggestion_clean = {
        str(key): value
        for key, value in suggested_action.items()
        if str(key) not in shared_drop_keys | {"caso"}
    }

    structured_record = structured_clean.get("numero_registro")
    if (
        "numero_registro" in suggestion_clean
        and suggestion_clean.get("numero_registro") == structured_record
    ):
        suggestion_clean.pop("numero_registro", None)

    return structured_clean, suggestion_clean


def build_room2_case_decision_instructions_message(
    *,
    case_id: UUID,
    agency_record_number: str | None = None,
    patient_name: str | None = None,
) -> str:
    """Build Room-2 guidance message that points doctors to the copy template."""

    identification_block = build_human_identification_block(
        agency_record_number=agency_record_number,
        patient_name=patient_name,
    )
    return (
        "# Instrução de decisão médica\n\n"
        f"{identification_block}\n\n"
        "1. Copie a PRÓXIMA mensagem (modelo puro).\n"
        "2. Responda como resposta a ela, preenchendo os campos.\n"
        "3. Mantenha exatamente uma linha por campo.\n\n"
        "Regras:\n"
        "- Pode usar com ou sem espaço após ':' (ex.: decisão:aceitar)\n"
        "- decisão=negar exige suporte=nenhum\n"
        "- valores válidos: decisão=aceitar|negar; suporte=nenhum|anestesista|anestesista_uti\n"
        "- Não adicione linhas fora do modelo\n"
        "- Use a mensagem de modelo para preencher o campo de caso"
    )


def build_room2_case_decision_instructions_formatted_html(
    *,
    case_id: UUID,
    agency_record_number: str | None = None,
    patient_name: str | None = None,
) -> str:
    """Build Room-2 guidance HTML payload that points doctors to template message."""

    identification_html = _build_human_identification_html_multiline(
        agency_record_number=agency_record_number,
        patient_name=patient_name,
    )
    return (
        "<h1>Instrução de decisão médica</h1>"
        f"{identification_html}"
        "<ol>"
        "<li>Copie a <strong>PRÓXIMA mensagem</strong> (modelo puro).</li>"
        "<li>Responda como resposta a ela, preenchendo os campos.</li>"
        "<li>Mantenha exatamente uma linha por campo.</li>"
        "</ol>"
        "<h2>Regras:</h2>"
        "<ul>"
        "<li>Pode usar com ou sem espaço após ':' (ex.: decisão:aceitar)</li>"
        "<li>decisão=negar exige suporte=nenhum</li>"
        "<li>valores válidos: decisão=aceitar|negar; "
        "suporte=nenhum|anestesista|anestesista_uti</li>"
        "<li>Não adicione linhas fora do modelo</li>"
        "<li>Use a mensagem de modelo para preencher o campo de caso</li>"
        "</ul>"
    )


def build_room2_case_decision_template_message(
    *,
    case_id: UUID,
    agency_record_number: str | None = None,
    patient_name: str | None = None,
) -> str:
    """Build strict Room-2 doctor reply template with human identification context."""

    identification_block = build_human_identification_block(
        agency_record_number=agency_record_number,
        patient_name=patient_name,
    )

    return (
        f"{identification_block}\n"
        "decisao: aceitar\n"
        "fluxo de admissao: agendamento\n"
        "suporte: nenhum\n"
        "motivo: (opcional)\n"
        f"caso: {case_id}"
    )


def build_room2_case_decision_template_formatted_html(
    *,
    case_id: UUID,
    agency_record_number: str | None = None,
    patient_name: str | None = None,
) -> str:
    """Build strict Room-2 doctor reply template HTML payload without code fencing."""

    identification_block = build_human_identification_block(
        agency_record_number=agency_record_number,
        patient_name=patient_name,
    )
    identification_lines_html = "<br>".join(
        escape(line) for line in identification_block.splitlines()
    )
    case_value = escape(str(case_id))
    return (
        "<p>"
        f"{identification_lines_html}<br>"
        "decisao: aceitar<br>"
        "fluxo de admissao: agendamento<br>"
        "suporte: nenhum<br>"
        "motivo: (opcional)<br>"
        f"caso: {case_value}"
        "</p>"
    )


def build_room2_ack_message(
    *,
    case_id: UUID,
    agency_record_number: str | None = None,
    patient_name: str | None = None,
) -> str:
    """Build Room-2 ack body used as audit-only reaction target."""

    identification_block = build_human_identification_block(
        agency_record_number=agency_record_number,
        patient_name=patient_name,
    )
    return f"Triagem registrada\n{identification_block}\nReaja com +1 para confirmar."


def build_room2_decision_ack_message(
    *,
    case_id: UUID,
    decision: str,
    support_flag: str,
    admission_flow: str | None,
    reason: str | None,
    agency_record_number: str | None = None,
    patient_name: str | None = None,
) -> str:
    """Build Room-2 post-decision acknowledgment body for doctor reaction."""

    reason_value = reason or ""
    decision_label = _format_decision_value(decision)
    support_label = _format_support_value(support_flag)
    admission_flow_line = ""
    if decision == "accept" and admission_flow is not None:
        admission_flow_line = (
            f"fluxo de admissao: {_format_admission_flow_value(admission_flow)}\n"
        )
    identification_block = build_human_identification_block(
        agency_record_number=agency_record_number,
        patient_name=patient_name,
    )
    return (
        "resultado: sucesso\n"
        f"{identification_block}\n"
        f"decisao: {decision_label}\n"
        f"{admission_flow_line}"
        f"suporte: {support_label}\n"
        f"motivo: {reason_value}\n"
        "Reaja com +1 para confirmar ciência do encerramento."
    )


def build_room2_decision_error_message(*, case_id: UUID, error_code: str) -> str:
    """Build deterministic Room-2 decision error feedback with correction guidance."""

    guidance = _room2_decision_error_guidance(error_code=error_code)
    return (
        "resultado: erro\n"
        f"caso: {case_id}\n"
        f"codigo_erro: {error_code}\n"
        f"acao: {guidance}\n\n"
        "Modelo obrigatório:\n"
        "decisao: aceitar|negar\n"
        "fluxo de admissao: agendamento|vinda_imediata\n"
        "suporte: nenhum|anestesista|anestesista_uti\n"
        "motivo: <texto livre ou vazio>\n"
        f"caso: {case_id}"
    )


def _room2_decision_error_guidance(*, error_code: str) -> str:
    if error_code == "invalid_template":
        return "Responda novamente como resposta usando exatamente o modelo."
    if error_code == "authorization_failed":
        return "Apenas membros autorizados da Room-2 podem decidir; verifique acesso."
    if error_code == "state_conflict":
        return "Caso não está aguardando decisão médica; não reenvie decisão duplicada."
    return "Revise o modelo e tente novamente."


def _format_decision_value(value: str) -> str:
    if value == "accept":
        return "aceitar"
    if value == "deny":
        return "negar"
    return value


def _format_support_value(value: str) -> str:
    if value == "none":
        return "nenhum"
    if value == "anesthesist":
        return "anestesista"
    if value == "anesthesist_icu":
        return "anestesista_uti"
    return value


def _format_admission_flow_value(value: str) -> str:
    if value == "scheduled":
        return "agendamento"
    if value == "immediate":
        return "vinda_imediata"
    return value


def _format_supported_eda_subtype_value(value: str | None) -> str | None:
    if value == "standard":
        return "padrão"
    if value == "gastrostomy":
        return "gastrostomia"
    if value == "esophageal_dilation":
        return "dilatação esofágica"
    if value == "foreign_body":
        return "retirada de corpo estranho"
    if value is None:
        return None
    return value


def _format_pediatric_flag_value(value: bool | None) -> str | None:
    if value is True:
        return "sim"
    if value is False:
        return "não"
    return None


def _map_presentation_value(value: str) -> str:
    mapping = {
        "accept": "aceitar",
        "deny": "negar",
        "none": "nenhum",
        "anesthesist": "anestesista",
        "anesthesist_icu": "anestesista_uti",
        "yes": "sim",
        "no": "nao",
        "unknown": "indeterminado",
        "bleeding": "sangramento",
        "moderate": "moderado",
        "low": "baixo",
        "high": "alto",
    }
    return mapping.get(value, value)


def build_room3_request_message(
    *,
    case_id: UUID,
    agency_record_number: str | None,
    patient_name: str | None,
    patient_age: str | None,
    requested_exam: str | None,
    doctor_display_name: str | None = None,
    pediatric_flag: bool | None = None,
) -> str:
    """Build Room-3 guidance message that points scheduler to copy template."""

    _ = case_id
    identification_block = build_human_identification_heading_block(
        agency_record_number=agency_record_number,
        patient_name=patient_name,
    )
    details_block = _build_room3_details_block(
        patient_age=patient_age,
        requested_exam=requested_exam,
        doctor_display_name=doctor_display_name,
        pediatric_flag=pediatric_flag,
        include_doctor_line=True,
    )
    return (
        "Solicitacao de agendamento\n\n"
        f"{identification_block}\n"
        f"{details_block}\n\n"
        "1. Copie a PROXIMA mensagem (modelo puro).\n"
        "2. Responda como resposta a ela, preenchendo os campos.\n"
        "3. Mantenha exatamente uma linha por campo.\n\n"
        "Regras:\n"
        "- status=confirmado exige data_hora, local e instruções preenchidos\n"
        "- status=negado usa motivo opcional"
    )


def _format_room3_context_value(value: str | None) -> str:
    normalized = (value or "").strip()
    if not normalized:
        return "(vazio)"
    return normalized


def build_room3_reply_template_message(
    *,
    case_id: UUID,
    agency_record_number: str | None = None,
    patient_name: str | None = None,
) -> str:
    """Build Room-3 pure scheduler template message for copy/paste reply."""

    identification_block = build_human_identification_block(
        agency_record_number=agency_record_number,
        patient_name=patient_name,
    )
    return (
        f"{identification_block}\n"
        "status: confirmado\n"
        "data_hora: DD/MM/YYYY HH:MM\n"
        "local:\n"
        "instruções:\n"
        "motivo: (opcional; usado quando status=negado)\n"
        f"caso: {case_id}"
    )


def build_room3_ack_message(
    *,
    case_id: UUID,
    agency_record_number: str | None,
    patient_name: str | None,
    patient_age: str | None,
    requested_exam: str | None,
) -> str:
    """Build Room-3 ack body used as audit-only reaction target."""

    _ = case_id
    identification_block = build_human_identification_block(
        agency_record_number=agency_record_number,
        patient_name=patient_name,
    )
    details_block = _build_room3_details_block(
        patient_age=patient_age,
        requested_exam=requested_exam,
    )
    return (
        "Solicitacao de agendamento registrada\n"
        f"{identification_block}\n"
        f"{details_block}\n"
        "Reaja com +1 para confirmar ciência do encerramento."
    )


def build_room3_immediate_admission_message(
    *,
    agency_record_number: str | None,
    patient_name: str | None,
    patient_age: str | None,
    requested_exam: str | None,
    doctor_display_name: str | None = None,
    support_flag: str | None = None,
    supported_eda_subtype: str | None = None,
    pediatric_flag: bool | None = None,
) -> str:
    """Build Room-3 informational message for doctor-approved immediate admission."""

    identification_block = build_human_identification_heading_block(
        agency_record_number=agency_record_number,
        patient_name=patient_name,
    )
    details_block = _build_room3_details_block(
        patient_age=patient_age,
        requested_exam=requested_exam,
        doctor_display_name=doctor_display_name,
        support_flag=support_flag,
        supported_eda_subtype=supported_eda_subtype,
        pediatric_flag=pediatric_flag,
        include_doctor_line=True,
        include_support_line=True,
    )
    return (
        "Vinda imediata autorizada\n\n"
        f"{identification_block}\n"
        f"{details_block}\n\n"
        "Nao abrir agendamento para este caso. Comunicacao apenas para ciencia operacional."
    )


def build_room3_immediate_admission_ack_message(
    *,
    agency_record_number: str | None,
    patient_name: str | None,
    patient_age: str | None,
    requested_exam: str | None,
    doctor_display_name: str | None = None,
    support_flag: str | None = None,
    supported_eda_subtype: str | None = None,
    pediatric_flag: bool | None = None,
) -> str:
    """Build Room-3 audit-only acknowledgment target for immediate admission."""

    identification_block = build_human_identification_block(
        agency_record_number=agency_record_number,
        patient_name=patient_name,
    )
    details_block = _build_room3_details_block(
        patient_age=patient_age,
        requested_exam=requested_exam,
        doctor_display_name=doctor_display_name,
        support_flag=support_flag,
        supported_eda_subtype=supported_eda_subtype,
        pediatric_flag=pediatric_flag,
        include_doctor_line=True,
        include_support_line=True,
    )
    return (
        "Vinda imediata registrada\n"
        f"{identification_block}\n"
        f"{details_block}\n"
        "Reaja com +1 para confirmar ciência do encerramento."
    )


def build_room3_invalid_format_reprompt(
    *,
    case_id: UUID,
    agency_record_number: str | None = None,
    patient_name: str | None = None,
) -> str:
    """Build strict Room-3 reformat prompt for invalid scheduler replies."""

    identification_block = build_human_identification_block(
        agency_record_number=agency_record_number,
        patient_name=patient_name,
    )
    return (
        "Nao consegui interpretar sua resposta para este caso.\n\n"
        f"{identification_block}\n\n"
        "Copie o modelo abaixo, preencha os campos e responda nesta mensagem.\n\n"
        "status: confirmado|negado\n"
        "data_hora: DD/MM/YYYY HH:MM\n"
        "local:\n"
        "instruções:\n"
        "motivo: (opcional; usado quando status=negado)\n"
        f"caso: {case_id}"
    )


def build_room1_final_accepted_message(
    *,
    case_id: UUID,
    agency_record_number: str | None,
    patient_name: str | None,
    patient_age: str | None,
    requested_exam: str | None,
    appointment_at: datetime,
    location: str,
    instructions: str,
    doctor_display_name: str | None = None,
    support_flag: str | None = None,
    supported_eda_subtype: str | None = None,
    pediatric_flag: bool | None = None,
) -> str:
    """Build Room-1 accepted final reply template."""

    context_block = _build_case_context_block(
        case_id=case_id,
        agency_record_number=agency_record_number,
        patient_name=patient_name,
        patient_age=patient_age,
        requested_exam=requested_exam,
        doctor_display_name=doctor_display_name,
        support_flag=support_flag,
        supported_eda_subtype=supported_eda_subtype,
        pediatric_flag=pediatric_flag,
        include_doctor_line=doctor_display_name is not None,
        include_support_line=support_flag is not None,
    )
    return (
        "✅ aceito\n"
        f"{context_block}\n"
        f"agendamento: {appointment_at.strftime('%d-%m-%Y %H:%M')} BRT\n"
        f"local: {location}\n"
        f"instrucoes: {instructions}\n\n"
        "Reaja com +1 para confirmar ciência do encerramento."
    )


def build_room1_final_immediate_message(
    *,
    case_id: UUID,
    agency_record_number: str | None,
    patient_name: str | None,
    patient_age: str | None,
    requested_exam: str | None,
    doctor_display_name: str | None = None,
    support_flag: str | None = None,
    supported_eda_subtype: str | None = None,
    pediatric_flag: bool | None = None,
) -> str:
    """Build Room-1 immediate-admission final reply template."""

    context_block = _build_case_context_block(
        case_id=case_id,
        agency_record_number=agency_record_number,
        patient_name=patient_name,
        patient_age=patient_age,
        requested_exam=requested_exam,
        doctor_display_name=doctor_display_name,
        support_flag=support_flag,
        supported_eda_subtype=supported_eda_subtype,
        pediatric_flag=pediatric_flag,
        include_doctor_line=doctor_display_name is not None,
        include_support_line=support_flag is not None,
    )
    return (
        "✅ aceito com vinda imediata autorizada\n"
        f"{context_block}\n\n"
        "Reaja com +1 para confirmar ciência do encerramento."
    )


def build_room1_final_denied_triage_message(
    *,
    case_id: UUID,
    agency_record_number: str | None,
    patient_name: str | None,
    patient_age: str | None,
    requested_exam: str | None,
    reason: str,
) -> str:
    """Build Room-1 triage denied final reply template."""

    context_block = _build_case_context_block(
        case_id=case_id,
        agency_record_number=agency_record_number,
        patient_name=patient_name,
        patient_age=patient_age,
        requested_exam=requested_exam,
    )
    return (
        "❌ negado (triagem)\n"
        f"{context_block}\n"
        f"motivo: {reason}\n\n"
        "Reaja com +1 para confirmar ciência do encerramento."
    )


def build_room1_final_denied_appointment_message(
    *,
    case_id: UUID,
    agency_record_number: str | None,
    patient_name: str | None,
    patient_age: str | None,
    requested_exam: str | None,
    reason: str,
) -> str:
    """Build Room-1 appointment denied final reply template."""

    context_block = _build_case_context_block(
        case_id=case_id,
        agency_record_number=agency_record_number,
        patient_name=patient_name,
        patient_age=patient_age,
        requested_exam=requested_exam,
    )
    return (
        "❌ negado (agendamento)\n"
        f"{context_block}\n"
        f"motivo: {reason}\n\n"
        "Reaja com +1 para confirmar ciência do encerramento."
    )


def build_room1_final_failure_message(
    *,
    case_id: UUID,
    agency_record_number: str | None,
    patient_name: str | None,
    patient_age: str | None,
    requested_exam: str | None,
    cause: str,
    details: str,
) -> str:
    """Build Room-1 processing failed final reply template."""

    context_block = _build_case_context_block(
        case_id=case_id,
        agency_record_number=agency_record_number,
        patient_name=patient_name,
        patient_age=patient_age,
        requested_exam=requested_exam,
    )
    return (
        "⚠️ falha no processamento\n"
        f"{context_block}\n"
        f"causa: {cause}\n"
        f"detalhes: {details}\n\n"
        "Reaja com +1 para confirmar ciência do encerramento."
    )


def build_room1_final_scope_manual_review_message(
    *,
    case_id: UUID,
    agency_record_number: str | None,
    patient_name: str | None,
    patient_age: str | None,
    requested_exam: str | None,
    reason_text: str,
) -> str:
    """Build Room-1 final reply for scope-gated manual-review-required cases."""

    context_block = _build_case_context_block(
        case_id=case_id,
        agency_record_number=agency_record_number,
        patient_name=patient_name,
        patient_age=patient_age,
        requested_exam=requested_exam,
    )
    return (
        "⚠️ revisão manual obrigatória (escopo EDA)\n"
        f"{context_block}\n"
        f"motivo: {reason_text}\n\n"
        "Reaja com +1 para confirmar ciência do encerramento."
    )


def _build_case_context_block(
    *,
    case_id: UUID,
    agency_record_number: str | None,
    patient_name: str | None,
    patient_age: str | None,
    requested_exam: str | None,
    doctor_display_name: str | None = None,
    support_flag: str | None = None,
    supported_eda_subtype: str | None = None,
    pediatric_flag: bool | None = None,
    include_doctor_line: bool = False,
    include_support_line: bool = False,
) -> str:
    _ = case_id
    identification_block = build_human_identification_block(
        agency_record_number=agency_record_number,
        patient_name=patient_name,
    )
    details_block = _build_room3_details_block(
        patient_age=patient_age,
        requested_exam=requested_exam,
        doctor_display_name=doctor_display_name,
        support_flag=support_flag,
        supported_eda_subtype=supported_eda_subtype,
        pediatric_flag=pediatric_flag,
        include_doctor_line=include_doctor_line,
        include_support_line=include_support_line,
    )
    return (
        f"{identification_block}\n"
        f"{details_block}"
    )


def _build_room3_details_block(
    *,
    patient_age: str | None,
    requested_exam: str | None,
    doctor_display_name: str | None = None,
    support_flag: str | None = None,
    supported_eda_subtype: str | None = None,
    pediatric_flag: bool | None = None,
    include_doctor_line: bool = False,
    include_support_line: bool = False,
) -> str:
    lines = [
        f"idade: {_format_room3_context_value(patient_age)}",
        f"exame solicitado: {_format_room3_context_value(requested_exam)}",
    ]

    subtype_label = _format_supported_eda_subtype_value(supported_eda_subtype)
    if subtype_label is not None:
        lines.append(f"subtipo EDA: {subtype_label}")

    pediatric_label = _format_pediatric_flag_value(pediatric_flag)
    if pediatric_label is not None:
        lines.append(f"paciente pediátrico: {pediatric_label}")

    if include_doctor_line:
        doctor_line = (
            f"aceito por: {_format_room3_context_value(doctor_display_name)}"
            if doctor_display_name is not None
            else "aceito por: não informado"
        )
        lines.append(doctor_line)

    if include_support_line:
        support_label = (
            _format_support_value(support_flag)
            if support_flag is not None
            else "não informado"
        )
        lines.append(f"suporte: {support_label}")

    return "\n".join(lines)


def _normalize_record_number_for_filename(value: str | None) -> str:
    normalized = (value or "").strip()
    if not normalized:
        return "indisponivel"
    slug_chars: list[str] = []
    for char in normalized:
        if char.isalnum():
            slug_chars.append(char.lower())
            continue
        slug_chars.append("-")
    slug = "".join(slug_chars).strip("-")
    if not slug:
        return "indisponivel"
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug
