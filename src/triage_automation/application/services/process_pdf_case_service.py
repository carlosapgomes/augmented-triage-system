"""Service layer for process_pdf_case job (download + extract segment)."""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from triage_automation.application.ports.audit_repository_port import (
    AuditEventCreateInput,
    AuditRepositoryPort,
)
from triage_automation.application.ports.case_repository_port import CaseRepositoryPort
from triage_automation.application.ports.job_queue_port import JobEnqueueInput, JobQueuePort
from triage_automation.application.services.llm1_service import (
    Llm1RetriableError,
    Llm1Service,
)
from triage_automation.application.services.llm2_service import (
    Llm2RetriableError,
    Llm2Service,
)
from triage_automation.domain.case_status import CaseStatus
from triage_automation.domain.policy.eda_preop_policy import evaluate_eda_preop_policy
from triage_automation.domain.record_number import (
    extract_and_strip_agency_record_number,
)
from triage_automation.infrastructure.matrix.mxc_downloader import (
    MatrixMxcDownloader,
    MxcDownloadError,
)
from triage_automation.infrastructure.pdf.text_extractor import (
    PdfTextExtractionError,
    PdfTextExtractor,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProcessPdfCaseRetriableError(RuntimeError):
    """Retriable processing error with explicit failure cause category."""

    cause: str
    details: str

    def __str__(self) -> str:
        return f"{self.cause}: {self.details}"


class ProcessPdfCaseService:
    """Run download/extraction stages for PDF case processing."""

    def __init__(
        self,
        *,
        case_repository: CaseRepositoryPort,
        mxc_downloader: MatrixMxcDownloader,
        text_extractor: PdfTextExtractor,
        llm1_service: Llm1Service | None = None,
        llm2_service: Llm2Service | None = None,
        audit_repository: AuditRepositoryPort | None = None,
        job_queue: JobQueuePort | None = None,
    ) -> None:
        if llm2_service is not None and job_queue is None:
            raise ValueError("job_queue is required when llm2_service is enabled")

        self._case_repository = case_repository
        self._mxc_downloader = mxc_downloader
        self._text_extractor = text_extractor
        self._llm1_service = llm1_service
        self._llm2_service = llm2_service
        self._audit_repository = audit_repository
        self._job_queue = job_queue

    async def process_case(self, *, case_id: UUID, pdf_mxc_url: str) -> str:
        """Download and extract case PDF content with retriable failure mapping."""

        logger.info("process_pdf_case_started case_id=%s mxc_url=%s", case_id, pdf_mxc_url)
        await self._case_repository.update_status(case_id=case_id, status=CaseStatus.EXTRACTING)

        try:
            pdf_bytes = await self._mxc_downloader.download_pdf(pdf_mxc_url)
        except MxcDownloadError as error:
            logger.warning("process_pdf_case_download_failed case_id=%s error=%s", case_id, error)
            raise ProcessPdfCaseRetriableError(cause="download", details=str(error)) from error
        logger.info("process_pdf_case_download_ok case_id=%s bytes=%s", case_id, len(pdf_bytes))

        try:
            extracted_text = self._text_extractor.extract_text(pdf_bytes)
            if not extracted_text:
                raise PdfTextExtractionError("PDF extraction produced empty text")
        except PdfTextExtractionError as error:
            logger.warning("process_pdf_case_extract_failed case_id=%s error=%s", case_id, error)
            raise ProcessPdfCaseRetriableError(cause="extract", details=str(error)) from error
        logger.info(
            "process_pdf_case_extract_ok case_id=%s text_chars=%s",
            case_id,
            len(extracted_text),
        )
        record_result = extract_and_strip_agency_record_number(extracted_text)
        logger.info(
            "process_pdf_case_record_extract_ok case_id=%s agency_record_number=%s",
            case_id,
            record_result.agency_record_number,
        )
        await self._case_repository.append_case_report_transcript(
            case_id=case_id,
            extracted_text=record_result.cleaned_text,
        )
        logger.info("process_pdf_case_report_transcript_appended case_id=%s", case_id)

        await self._case_repository.store_pdf_extraction(
            case_id=case_id,
            pdf_mxc_url=pdf_mxc_url,
            extracted_text=record_result.cleaned_text,
            agency_record_number=record_result.agency_record_number,
            agency_record_extracted_at=datetime.now(tz=UTC),
        )
        logger.info("process_pdf_case_persist_pdf_ok case_id=%s", case_id)

        if self._llm1_service is not None:
            await self._case_repository.update_status(case_id=case_id, status=CaseStatus.LLM_STRUCT)
            logger.info("process_pdf_case_llm1_started case_id=%s", case_id)
            try:
                llm1_result = await self._llm1_service.run(
                    case_id=case_id,
                    agency_record_number=record_result.agency_record_number,
                    clean_text=record_result.cleaned_text,
                    interaction_repository=self._case_repository,
                )
            except Llm1RetriableError as error:
                if self._audit_repository is not None:
                    await self._audit_repository.append_event(
                        AuditEventCreateInput(
                            case_id=case_id,
                            actor_type="system",
                            event_type="LLM1_FAILED",
                            payload={"error": str(error)},
                        )
                    )
                logger.warning("process_pdf_case_llm1_failed case_id=%s error=%s", case_id, error)
                raise ProcessPdfCaseRetriableError(cause="llm1", details=str(error)) from error

            await self._case_repository.store_llm1_artifacts(
                case_id=case_id,
                structured_data_json=llm1_result.structured_data_json,
                summary_text=llm1_result.summary_text,
            )
            logger.info(
                (
                    "process_pdf_case_llm1_ok case_id=%s "
                    "prompt_system=%s@%s prompt_user=%s@%s"
                ),
                case_id,
                llm1_result.prompt_system_name,
                llm1_result.prompt_system_version,
                llm1_result.prompt_user_name,
                llm1_result.prompt_user_version,
            )
            if self._audit_repository is not None:
                await self._audit_repository.append_event(
                    AuditEventCreateInput(
                        case_id=case_id,
                        actor_type="system",
                        event_type="LLM1_STRUCTURED_SUMMARY_OK",
                        payload=build_llm_prompt_version_audit_payload(
                            system_prompt_name=llm1_result.prompt_system_name,
                            system_prompt_version=llm1_result.prompt_system_version,
                            user_prompt_name=llm1_result.prompt_user_name,
                            user_prompt_version=llm1_result.prompt_user_version,
                        ),
                    )
                )

            if self._llm2_service is not None:
                scope_gate_payload = build_scope_gated_manual_review_payload(
                    case_id=case_id,
                    agency_record_number=record_result.agency_record_number,
                    llm1_structured_data=llm1_result.structured_data_json,
                    cleaned_text=record_result.cleaned_text,
                )
                await self._case_repository.update_status(
                    case_id=case_id,
                    status=CaseStatus.LLM_SUGGEST,
                )

                if scope_gate_payload is not None:
                    scope_gate_payload = _with_preop_gate_block(
                        suggested_action_json=scope_gate_payload,
                        preop_gate_payload={
                            "decision": scope_gate_payload.get(
                                "decision",
                                "manual_review_required",
                            ),
                            "reason_code": scope_gate_payload.get(
                                "reason_code",
                                "manual_review_required_insufficient_data",
                            ),
                            "reason_text": scope_gate_payload.get(
                                "reason_text",
                                "Revisao manual obrigatoria por escopo nao deterministico.",
                            ),
                            "evidence_spans": scope_gate_payload.get("evidence_spans", []),
                        },
                    )
                    await self._case_repository.store_llm2_artifacts(
                        case_id=case_id,
                        suggested_action_json=scope_gate_payload,
                    )
                    logger.info(
                        "process_pdf_case_scope_gate_manual_review case_id=%s reason_code=%s",
                        case_id,
                        scope_gate_payload.get("reason_code"),
                    )
                    logger.info(
                        (
                            "process_pdf_case_skipped_llm2_for_scope_gate "
                            "case_id=%s exam_scope=%s"
                        ),
                        case_id,
                        scope_gate_payload.get("exam_type"),
                    )
                    if self._audit_repository is not None:
                        await self._audit_repository.append_event(
                            AuditEventCreateInput(
                                case_id=case_id,
                                actor_type="system",
                                event_type="EDA_SCOPE_GATED_MANUAL_REVIEW",
                                payload={
                                    "decision": scope_gate_payload.get("decision"),
                                    "reason_code": scope_gate_payload.get("reason_code"),
                                    "reason_text": scope_gate_payload.get("reason_text"),
                                    "exam_type": scope_gate_payload.get("exam_type"),
                                    "evidence_spans": scope_gate_payload.get("evidence_spans", []),
                                },
                            )
                        )

                    assert self._job_queue is not None  # ensured by __init__
                    await self._job_queue.enqueue(
                        JobEnqueueInput(
                            job_type="post_room1_final_scope_manual_review",
                            case_id=case_id,
                            payload={
                                "reason_code": scope_gate_payload.get("reason_code"),
                                "reason_text": scope_gate_payload.get("reason_text"),
                                "exam_type": scope_gate_payload.get("exam_type"),
                            },
                        )
                    )
                    logger.info(
                        (
                            "process_pdf_case_enqueued_next_job case_id=%s "
                            "job_type=post_room1_final_scope_manual_review"
                        ),
                        case_id,
                    )
                else:
                    logger.info("process_pdf_case_llm2_started case_id=%s", case_id)
                    try:
                        llm2_result = await self._llm2_service.run(
                            case_id=case_id,
                            agency_record_number=record_result.agency_record_number,
                            llm1_structured_data=llm1_result.structured_data_json,
                            interaction_repository=self._case_repository,
                        )
                    except Llm2RetriableError as error:
                        if self._audit_repository is not None:
                            await self._audit_repository.append_event(
                                AuditEventCreateInput(
                                    case_id=case_id,
                                    actor_type="system",
                                    event_type="LLM2_FAILED",
                                    payload={"error": str(error)},
                                )
                            )
                        logger.warning(
                            "process_pdf_case_llm2_failed case_id=%s error=%s",
                            case_id,
                            error,
                        )
                        raise ProcessPdfCaseRetriableError(
                            cause="llm2",
                            details=str(error),
                        ) from error

                    deterministic_preop_gate = evaluate_eda_preop_policy(
                        structured_data=llm1_result.structured_data_json
                    )
                    llm2_suggested_action_json = _with_preop_gate_block(
                        suggested_action_json=llm2_result.suggested_action_json,
                        preop_gate_payload=deterministic_preop_gate,
                    )

                    await self._case_repository.store_llm2_artifacts(
                        case_id=case_id,
                        suggested_action_json=llm2_suggested_action_json,
                    )
                    logger.info(
                        (
                            "process_pdf_case_llm2_ok case_id=%s suggestion=%s "
                            "prompt_system=%s@%s prompt_user=%s@%s contradictions=%s"
                        ),
                        case_id,
                        llm2_suggested_action_json.get("suggestion"),
                        llm2_result.prompt_system_name,
                        llm2_result.prompt_system_version,
                        llm2_result.prompt_user_name,
                        llm2_result.prompt_user_version,
                        len(llm2_result.contradictions),
                    )
                    if self._audit_repository is not None:
                        llm2_payload = build_llm_prompt_version_audit_payload(
                            system_prompt_name=llm2_result.prompt_system_name,
                            system_prompt_version=llm2_result.prompt_system_version,
                            user_prompt_name=llm2_result.prompt_user_name,
                            user_prompt_version=llm2_result.prompt_user_version,
                        )
                        llm2_payload["suggestion"] = llm2_suggested_action_json.get(
                            "suggestion"
                        )
                        await self._audit_repository.append_event(
                            AuditEventCreateInput(
                                case_id=case_id,
                                actor_type="system",
                                event_type="LLM2_SUGGESTION_OK",
                                payload=llm2_payload,
                            )
                        )

                    if llm2_result.contradictions and self._audit_repository is not None:
                        await self._audit_repository.append_event(
                            AuditEventCreateInput(
                                case_id=case_id,
                                actor_type="system",
                                event_type="LLM_CONTRADICTION_DETECTED",
                                payload={"contradictions": llm2_result.contradictions},
                            )
                        )

                    assert self._job_queue is not None  # ensured by __init__
                    await self._job_queue.enqueue(
                        JobEnqueueInput(
                            job_type="post_room2_widget",
                            case_id=case_id,
                            payload={},
                        )
                    )
                    logger.info(
                        "process_pdf_case_enqueued_next_job case_id=%s job_type=post_room2_widget",
                        case_id,
                    )

        logger.info("process_pdf_case_completed case_id=%s", case_id)
        return record_result.cleaned_text


def _extract_preop_exam_type(*, llm1_structured_data: dict[str, object]) -> str | None:
    preop_screening = llm1_structured_data.get("preop_screening")
    if not isinstance(preop_screening, dict):
        return None
    exam_type = preop_screening.get("exam_type")
    if isinstance(exam_type, str):
        normalized = exam_type.strip().lower()
        if normalized in {"eda", "non_eda", "unknown"}:
            return normalized
    return None


def _extract_preop_evidence_spans(
    *,
    llm1_structured_data: dict[str, object],
) -> list[dict[str, str]]:
    preop_screening = llm1_structured_data.get("preop_screening")
    if not isinstance(preop_screening, dict):
        return []

    evidence_spans_raw = preop_screening.get("evidence_spans")
    if not isinstance(evidence_spans_raw, list):
        return []

    evidence_spans: list[dict[str, str]] = []
    for item in evidence_spans_raw:
        if not isinstance(item, dict):
            continue
        field_path = item.get("field_path")
        excerpt = item.get("excerpt")
        if not isinstance(field_path, str) or not isinstance(excerpt, str):
            continue
        normalized_field_path = field_path.strip()
        normalized_excerpt = excerpt.strip()
        if not normalized_field_path or not normalized_excerpt:
            continue
        evidence_spans.append(
            {"field_path": normalized_field_path, "excerpt": normalized_excerpt}
        )
    return evidence_spans


def _with_preop_gate_block(
    *,
    suggested_action_json: dict[str, object],
    preop_gate_payload: dict[str, object],
) -> dict[str, object]:
    decision_raw = preop_gate_payload.get("decision")
    reason_code_raw = preop_gate_payload.get("reason_code")
    reason_text_raw = preop_gate_payload.get("reason_text")
    evidence_spans_raw = preop_gate_payload.get("evidence_spans")

    decision = str(decision_raw) if isinstance(decision_raw, str) else "manual_review_required"
    reason_code = (
        str(reason_code_raw)
        if isinstance(reason_code_raw, str)
        else "manual_review_required_insufficient_data"
    )
    reason_text = (
        str(reason_text_raw)
        if isinstance(reason_text_raw, str)
        else "Dados insuficientes para gate pre-procedimento deterministico."
    )
    evidence_spans = evidence_spans_raw if isinstance(evidence_spans_raw, list) else []

    payload = dict(suggested_action_json)
    payload["preop_gate"] = {
        "decision": decision,
        "reason_code": reason_code,
        "reason_text": reason_text,
        "evidence_spans": evidence_spans,
    }
    return payload


_SUPPORTED_EDA_SUBTYPES = {
    "standard",
    "gastrostomy",
    "esophageal_dilation",
    "foreign_body",
}

_SCOPE_GASTROSTOMY_TERMS = (
    "gtt",
    "gastrostomia",
    "gastrostomy",
    "confeccao de gtt",
    "programar gtt",
)

_SCOPE_ESOPHAGEAL_DILATION_TERMS = (
    "dilatacao esofagica",
    "dilatacao de esofago",
    "dilatacao do esofago",
)

_SCOPE_FOREIGN_BODY_TERMS = (
    "corpo estranho",
    "retirada de corpo estranho",
)

_SCOPE_EXPLICIT_EDA_TERMS = (
    "endoscopia digestiva alta",
    "solicitacao de endoscopia digestiva alta",
    "endoscopia digestiva alta - eda",
    "videoendoscopia digestiva alta",
    "endoscopia digestiva superior",
)


def _normalize_scope_keyword_text(*, value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    without_diacritics = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    collapsed_whitespace = " ".join(without_diacritics.lower().split())
    return collapsed_whitespace


def _contains_scope_term(*, normalized_text: str, term: str) -> bool:
    if " " in term:
        return term in normalized_text
    return re.search(rf"\b{re.escape(term)}\b", normalized_text) is not None


def _extract_scope_keyword_candidate_texts(
    *,
    llm1_structured_data: dict[str, object],
    cleaned_text: str,
) -> list[str]:
    candidate_texts: list[str] = [cleaned_text]

    eda_payload = llm1_structured_data.get("eda")
    if isinstance(eda_payload, dict):
        requested_procedure = eda_payload.get("requested_procedure")
        if isinstance(requested_procedure, dict):
            requested_name = requested_procedure.get("name")
            if isinstance(requested_name, str) and requested_name.strip():
                candidate_texts.append(requested_name)

    summary_payload = llm1_structured_data.get("summary")
    if isinstance(summary_payload, dict):
        one_liner = summary_payload.get("one_liner")
        if isinstance(one_liner, str) and one_liner.strip():
            candidate_texts.append(one_liner)
        bullet_points = summary_payload.get("bullet_points")
        if isinstance(bullet_points, list):
            candidate_texts.extend(
                point
                for point in bullet_points
                if isinstance(point, str) and point.strip()
            )

    for span in _extract_preop_evidence_spans(llm1_structured_data=llm1_structured_data):
        excerpt = span.get("excerpt")
        if isinstance(excerpt, str) and excerpt.strip():
            candidate_texts.append(excerpt)

    return candidate_texts


def _extract_supported_eda_subtype_from_llm1(
    *,
    llm1_structured_data: dict[str, object],
) -> str | None:
    eda_payload = llm1_structured_data.get("eda")
    if isinstance(eda_payload, dict):
        requested_procedure = eda_payload.get("requested_procedure")
        if isinstance(requested_procedure, dict):
            subtype = requested_procedure.get("subtype")
            if isinstance(subtype, str):
                normalized = subtype.strip().lower()
                if normalized in _SUPPORTED_EDA_SUBTYPES:
                    return normalized

    preop_screening = llm1_structured_data.get("preop_screening")
    if not isinstance(preop_screening, dict):
        return None
    rulebook_signals = preop_screening.get("rulebook_signals")
    if not isinstance(rulebook_signals, dict):
        return None
    subtype = rulebook_signals.get("eda_subtype")
    if not isinstance(subtype, str):
        return None
    normalized = subtype.strip().lower()
    if normalized in _SUPPORTED_EDA_SUBTYPES:
        return normalized
    return None


def _detect_supported_eda_scope_keyword(
    *,
    llm1_structured_data: dict[str, object],
    cleaned_text: str,
) -> tuple[str | None, str | None]:
    candidate_texts = _extract_scope_keyword_candidate_texts(
        llm1_structured_data=llm1_structured_data,
        cleaned_text=cleaned_text,
    )

    for candidate in candidate_texts:
        normalized_candidate = _normalize_scope_keyword_text(value=candidate)
        for term in _SCOPE_FOREIGN_BODY_TERMS:
            if _contains_scope_term(normalized_text=normalized_candidate, term=term):
                return "foreign_body", term
        for term in _SCOPE_GASTROSTOMY_TERMS:
            if _contains_scope_term(normalized_text=normalized_candidate, term=term):
                return "gastrostomy", term
        for term in _SCOPE_ESOPHAGEAL_DILATION_TERMS:
            if _contains_scope_term(normalized_text=normalized_candidate, term=term):
                return "esophageal_dilation", term

    return None, None


def _detect_explicit_eda_scope_keyword(
    *,
    llm1_structured_data: dict[str, object],
    cleaned_text: str,
) -> tuple[bool, str | None]:
    candidate_texts = _extract_scope_keyword_candidate_texts(
        llm1_structured_data=llm1_structured_data,
        cleaned_text=cleaned_text,
    )

    for candidate in candidate_texts:
        normalized_candidate = _normalize_scope_keyword_text(value=candidate)

        for term in _SCOPE_EXPLICIT_EDA_TERMS:
            if _contains_scope_term(normalized_text=normalized_candidate, term=term):
                return True, term

        has_eda_acronym = (
            re.search(r"\beda\b", normalized_candidate) is not None
            or re.search(r"\be\s*[.\-]?\s*d\s*[.\-]?\s*a\b", normalized_candidate)
            is not None
        )
        has_request_context = (
            re.search(
                r"\b(motivo|solicit|exame|encaminhamento|procedimento)\b",
                normalized_candidate,
            )
            is not None
        )
        if has_eda_acronym and has_request_context:
            return True, "eda"

    return False, None


def _append_scope_keyword_evidence_span(
    *,
    evidence_spans: list[dict[str, str]],
    scope_keyword_type: str,
    matched_term: str,
) -> list[dict[str, str]]:
    scope_label = (
        "gastrostomia/GTT" if scope_keyword_type == "gastrostomy" else "dilatacao esofagica"
    )
    keyword_span = {
        "field_path": "scope_detection.keyword",
        "excerpt": (
            f"Termo de escopo detectado no relatorio: {matched_term} ({scope_label})."
        ),
    }
    if keyword_span in evidence_spans:
        return evidence_spans
    return [*evidence_spans, keyword_span]


def build_scope_gated_manual_review_payload(
    *,
    case_id: UUID,
    agency_record_number: str,
    llm1_structured_data: dict[str, object],
    cleaned_text: str,
) -> dict[str, object] | None:
    """Build deterministic manual-review payload for unresolved non-supported scope."""

    exam_type = _extract_preop_exam_type(llm1_structured_data=llm1_structured_data)
    supported_subtype = _extract_supported_eda_subtype_from_llm1(
        llm1_structured_data=llm1_structured_data,
    )
    if supported_subtype is None:
        supported_subtype, _ = _detect_supported_eda_scope_keyword(
            llm1_structured_data=llm1_structured_data,
            cleaned_text=cleaned_text,
        )

    explicit_eda_detected, _ = _detect_explicit_eda_scope_keyword(
        llm1_structured_data=llm1_structured_data,
        cleaned_text=cleaned_text,
    )

    if supported_subtype is not None or explicit_eda_detected:
        exam_type = "eda"

    if exam_type not in {"non_eda", "unknown"}:
        return None

    reason_code = "non_eda_request" if exam_type == "non_eda" else "unknown_exam_type"
    reason_text = (
        "Relatorio fora de escopo EDA; revisao manual obrigatoria."
        if exam_type == "non_eda"
        else "Tipo de exame nao identificado; revisao manual obrigatoria."
    )

    evidence_spans = _extract_preop_evidence_spans(
        llm1_structured_data=llm1_structured_data
    )

    return {
        "schema_version": "1.1",
        "language": "pt-BR",
        "case_id": str(case_id),
        "agency_record_number": agency_record_number,
        "decision": "manual_review_required",
        "suggestion": "manual_review_required",
        "reason_code": reason_code,
        "reason_text": reason_text,
        "exam_type": exam_type,
        "evidence_spans": evidence_spans,
    }


def build_llm_prompt_version_audit_payload(
    *,
    system_prompt_name: str,
    system_prompt_version: int,
    user_prompt_name: str,
    user_prompt_version: int,
) -> dict[str, object]:
    """Build deterministic audit payload with prompt template names and versions."""

    return {
        "prompt_system_name": system_prompt_name,
        "prompt_system_version": system_prompt_version,
        "prompt_user_name": user_prompt_name,
        "prompt_user_version": user_prompt_version,
    }
