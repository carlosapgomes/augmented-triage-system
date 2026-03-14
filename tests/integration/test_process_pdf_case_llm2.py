from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.config import Config

from alembic import command
from triage_automation.application.ports.case_repository_port import CaseCreateInput
from triage_automation.application.services.llm1_service import Llm1Service
from triage_automation.application.services.llm2_service import Llm2Service
from triage_automation.application.services.process_pdf_case_service import (
    ProcessPdfCaseRetriableError,
    ProcessPdfCaseService,
)
from triage_automation.domain.case_status import CaseStatus
from triage_automation.infrastructure.db.audit_repository import SqlAlchemyAuditRepository
from triage_automation.infrastructure.db.case_repository import SqlAlchemyCaseRepository
from triage_automation.infrastructure.db.job_queue_repository import SqlAlchemyJobQueueRepository
from triage_automation.infrastructure.db.session import create_session_factory
from triage_automation.infrastructure.llm.openai_client import (
    OpenAiChatCompletionsClient,
    OpenAiHttpResponse,
)
from triage_automation.infrastructure.matrix.mxc_downloader import MatrixMxcDownloader
from triage_automation.infrastructure.pdf.text_extractor import PdfTextExtractor


class FakeMatrixMediaClient:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    async def download_mxc(self, mxc_url: str) -> bytes:
        return self._payload


class FakeLlmClient:
    def __init__(self, response_text: str) -> None:
        self._response_text = response_text
        self.calls: list[tuple[str, str]] = []

    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self._response_text


class FakeOpenAiTransport:
    def __init__(self, payloads: list[dict[str, object]]) -> None:
        self._payloads = payloads

    async def request(
        self,
        *,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
        timeout_seconds: float,
    ) -> OpenAiHttpResponse:
        _ = method, url, headers, body, timeout_seconds
        payload = self._payloads.pop(0)
        return OpenAiHttpResponse(
            status_code=200,
            body_bytes=json.dumps(payload).encode("utf-8"),
        )


def _build_simple_pdf(text: str) -> bytes:
    stream = f"BT /F1 24 Tf 72 72 Td ({text}) Tj ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] "
        "/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    parts: list[bytes] = [b"%PDF-1.4\n"]
    offsets = [0]

    for idx, body in enumerate(objects, start=1):
        offsets.append(sum(len(part) for part in parts))
        parts.append(f"{idx} 0 obj\n{body}\nendobj\n".encode("latin-1"))

    xref_start = sum(len(part) for part in parts)
    size = len(objects) + 1

    xref_lines = [f"xref\n0 {size}\n", "0000000000 65535 f \n"]
    xref_lines.extend(f"{offset:010d} 00000 n \n" for offset in offsets[1:])
    trailer = (
        f"trailer\n<< /Size {size} /Root 1 0 R >>\n"
        f"startxref\n{xref_start}\n%%EOF\n"
    )

    parts.append("".join(xref_lines).encode("latin-1"))
    parts.append(trailer.encode("latin-1"))

    return b"".join(parts)


def _upgrade_head(tmp_path: Path, filename: str) -> tuple[str, str]:
    db_path = tmp_path / filename
    sync_url = f"sqlite+pysqlite:///{db_path}"
    async_url = f"sqlite+aiosqlite:///{db_path}"

    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(alembic_config, "head")

    return sync_url, async_url


def _valid_llm1_payload(agency_record_number: str) -> dict[str, object]:
    return {
        "schema_version": "1.1",
        "language": "pt-BR",
        "agency_record_number": agency_record_number,
        "patient": {"name": "Paciente", "age": 50, "sex": "F", "document_id": None},
        "eda": {
            "indication_category": "dyspepsia",
            "exclusion_type": "none",
            "is_pediatric": False,
            "foreign_body_suspected": False,
            "requested_procedure": {
                "name": "EDA",
                "urgency": "eletivo",
                "subtype": "standard",
            },
            "labs": {
                "hb_g_dl": 10.5,
                "hct_percent": 31.0,
                "platelets_per_mm3": 130000,
                "tp_seconds": 12.0,
                "inr": 1.2,
                "rni": 1.2,
                "ttpa_seconds": 30.0,
                "urea_mg_dl": 28.0,
                "creatinine_mg_dl": 0.9,
                "source_text_hint": None,
            },
            "ecg": {
                "report_present": "yes",
                "abnormal_flag": "no",
                "source_text_hint": None,
            },
            "asa": {"bucket": "I-II", "source_text_hint": "bom estado clinico"},
            "cardiovascular_risk": {"level": "low", "source_text_hint": "sem alto risco"},
        },
        "preop_screening": {
            "exam_type": "eda",
            "has_cardiovascular_disease": "no",
            "has_active_respiratory_symptoms": "no",
            "has_prior_respiratory_disease": "no",
            "has_ecg_report": "yes",
            "has_chest_xray_report": "yes",
            "has_echocardiogram_report": "unknown",
            "hb_g_dl": 10.5,
            "platelets_per_mm3": 130000,
            "inr": 1.2,
            "rulebook_signals": {
                "eda_subtype": "standard",
                "minimum_exam_evidence": {
                    "hb_or_hct_present": "yes",
                    "hb_numeric_present": "yes",
                    "platelets_numeric_present": "yes",
                    "tp_inr_rni_numeric_present": "yes",
                    "ttpa_present": "yes",
                    "urea_present": "yes",
                    "creatinine_present": "yes",
                    "coagulogram_normal_supports_ttpa": "no",
                    "renal_function_preserved_supports_urea_and_creatinine": "no",
                },
                "conditional_exam_requirements": {
                    "ecg_required": "yes",
                    "chest_xray_required": "unknown",
                    "echocardiogram_required": "unknown",
                    "ecg_report_finding_present": "yes",
                    "chest_xray_report_finding_present": "unknown",
                    "echocardiogram_report_finding_present": "unknown",
                },
                "clinical_flags": {
                    "hepatopathy_explicit": "no",
                    "cardiopathy_explicit": "no",
                    "known_cardiovascular_disease": "no",
                    "active_respiratory_symptoms": "no",
                    "prior_respiratory_disease": "no",
                    "multiple_comorbidities": "unknown",
                    "qt_prolonging_medications": "unknown",
                    "diabetes_mellitus": "unknown",
                    "explicit_obesity": "unknown",
                    "recent_chest_pain": "no",
                    "recent_dyspnea": "no",
                    "recent_palpitations": "no",
                    "recent_syncope": "no",
                    "unexplained_dyspnea": "unknown",
                    "heart_failure_signs": "unknown",
                    "new_or_unevaluated_murmur": "unknown",
                    "moderate_or_severe_valvulopathy_without_recent_echo": "unknown",
                    "worsening_cardiomyopathy": "unknown",
                    "pulmonary_hypertension": "unknown",
                    "prior_myocardial_infarction": "no",
                    "prior_coronary_bypass": "no",
                    "prior_coronary_angioplasty": "no",
                },
            },
        },
        "policy_precheck": {
            "excluded_from_eda_flow": False,
            "exclusion_reason": None,
            "labs_required": True,
            "labs_pass": "yes",
            "labs_failed_items": [],
            "ecg_required": True,
            "ecg_present": "yes",
            "pediatric_flag": False,
            "notes": None,
        },
        "summary": {"one_liner": "Resumo LLM1", "bullet_points": ["a", "b", "c"]},
        "extraction_quality": {"confidence": "media", "missing_fields": [], "notes": None},
    }


def _valid_llm2_payload(case_id: str, agency_record_number: str) -> dict[str, object]:
    return {
        "schema_version": "1.1",
        "language": "pt-BR",
        "case_id": case_id,
        "agency_record_number": agency_record_number,
        "suggestion": "accept",
        "support_recommendation": "none",
        "rationale": {
            "short_reason": "Apto para fluxo padrao",
            "details": ["criterio 1", "criterio 2"],
            "missing_info_questions": [],
        },
        "policy_alignment": {
            "excluded_request": False,
            "labs_ok": "yes",
            "ecg_ok": "yes",
            "pediatric_flag": False,
            "notes": None,
        },
        "confidence": "media",
    }


def _llm1_payload_with_exam_type(
    agency_record_number: str,
    *,
    exam_type: str,
    evidence_excerpt: str | None = None,
) -> dict[str, object]:
    payload = _valid_llm1_payload(agency_record_number)
    preop_screening = payload["preop_screening"]
    assert isinstance(preop_screening, dict)
    preop_screening["exam_type"] = exam_type
    preop_screening["evidence_spans"] = [
        {
            "field_path": "preop_screening.exam_type",
            "excerpt": (
                evidence_excerpt
                if evidence_excerpt is not None
                else f"solicitacao classificada como {exam_type}"
            ),
        }
    ]

    eda = payload["eda"]
    assert isinstance(eda, dict)
    requested_procedure = eda["requested_procedure"]
    assert isinstance(requested_procedure, dict)
    rulebook_signals = preop_screening["rulebook_signals"]
    assert isinstance(rulebook_signals, dict)

    if exam_type in {"non_eda", "unknown"}:
        requested_procedure["subtype"] = "unknown"
        rulebook_signals["eda_subtype"] = "unknown"
    else:
        requested_procedure["subtype"] = "standard"
        rulebook_signals["eda_subtype"] = "standard"
    return payload


def _decode_json(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        parsed = json.loads(value)
        assert isinstance(parsed, dict)
        return parsed
    assert isinstance(value, dict)
    return value


def _assert_preop_gate_contract(
    suggested_action: dict[str, Any],
    *,
    expected_decision: str,
) -> None:
    preop_gate = suggested_action.get("preop_gate")
    assert isinstance(preop_gate, dict)
    assert preop_gate.get("decision") == expected_decision
    assert isinstance(preop_gate.get("reason_code"), str)
    assert isinstance(preop_gate.get("reason_text"), str)
    evidence_spans = preop_gate.get("evidence_spans")
    assert isinstance(evidence_spans, list)


@pytest.mark.asyncio
async def test_llm2_persists_suggestion_and_enqueues_room2_widget_job(tmp_path: Path) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "llm2_ok.db")
    session_factory = create_session_factory(async_url)

    case_repo = SqlAlchemyCaseRepository(session_factory)
    queue_repo = SqlAlchemyJobQueueRepository(session_factory)

    case = await case_repo.create_case(
        CaseCreateInput(
            case_id=uuid4(),
            status=CaseStatus.R1_ACK_PROCESSING,
            room1_origin_room_id="!room1:example.org",
            room1_origin_event_id="$origin-llm2-1",
            room1_sender_user_id="@human:example.org",
        )
    )

    llm1_service = Llm1Service(
        llm_client=FakeLlmClient(json.dumps(_valid_llm1_payload("12345")))
    )
    llm2_service = Llm2Service(
        llm_client=FakeLlmClient(json.dumps(_valid_llm2_payload(str(case.case_id), "12345")))
    )

    service = ProcessPdfCaseService(
        case_repository=case_repo,
        mxc_downloader=MatrixMxcDownloader(
            FakeMatrixMediaClient(
                _build_simple_pdf(
                    "RELATORIO DE OCORRENCIAS 12345 " "clinical text 12345"
                )
            )
        ),
        text_extractor=PdfTextExtractor(),
        llm1_service=llm1_service,
        llm2_service=llm2_service,
        job_queue=queue_repo,
    )

    await service.process_case(case_id=case.case_id, pdf_mxc_url="mxc://example.org/pdf")

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        row = connection.execute(
            sa.text(
                "SELECT status, suggested_action_json "
                "FROM cases ORDER BY created_at DESC LIMIT 1"
            )
        ).mappings().one()
        interaction_rows = connection.execute(
            sa.text(
                "SELECT stage, input_payload, output_payload, "
                "prompt_system_name, prompt_system_version, "
                "prompt_user_name, prompt_user_version, model_name "
                "FROM case_llm_interactions "
                "WHERE case_id = :case_id "
                "ORDER BY id"
            ),
            {"case_id": case.case_id.hex},
        ).mappings().all()
        job_count = connection.execute(
            sa.text("SELECT COUNT(*) FROM jobs WHERE job_type = 'post_room2_widget'")
        ).scalar_one()

    suggested_action = _decode_json(row["suggested_action_json"])

    assert row["status"] == "LLM_SUGGEST"
    assert suggested_action["suggestion"] == "accept"
    assert suggested_action["support_recommendation"] == "none"
    asa = suggested_action.get("asa")
    assert isinstance(asa, dict)
    assert asa.get("bucket") == "I-II"
    assert asa.get("display_text") == "I-II"
    _assert_preop_gate_contract(suggested_action, expected_decision="accept")
    preop_gate = suggested_action["preop_gate"]
    assert isinstance(preop_gate, dict)
    assert preop_gate.get("decision") == suggested_action["suggestion"]
    assert job_count == 1
    assert len(interaction_rows) == 2

    llm1_row = interaction_rows[0]
    llm1_input = _decode_json(llm1_row["input_payload"])
    llm1_output = _decode_json(llm1_row["output_payload"])
    assert llm1_row["stage"] == "LLM1"
    assert llm1_row["prompt_system_name"] == "llm1_system"
    assert llm1_row["prompt_system_version"] == 0
    assert llm1_row["prompt_user_name"] == "llm1_user"
    assert llm1_row["prompt_user_version"] == 0
    assert llm1_row["model_name"] is None
    assert "system_prompt" in llm1_input
    assert "user_prompt" in llm1_input
    assert llm1_output["raw_response"] == json.dumps(_valid_llm1_payload("12345"))

    llm2_row = interaction_rows[1]
    llm2_input = _decode_json(llm2_row["input_payload"])
    llm2_output = _decode_json(llm2_row["output_payload"])
    assert llm2_row["stage"] == "LLM2"
    assert llm2_row["prompt_system_name"] == "llm2_system"
    assert llm2_row["prompt_system_version"] == 0
    assert llm2_row["prompt_user_name"] == "llm2_user"
    assert llm2_row["prompt_user_version"] == 0
    assert llm2_row["model_name"] is None
    assert "system_prompt" in llm2_input
    assert "user_prompt" in llm2_input
    assert str(case.case_id) in str(llm2_input["user_prompt"])
    assert llm2_output["raw_response"] == json.dumps(
        _valid_llm2_payload(str(case.case_id), "12345")
    )


@pytest.mark.asyncio
async def test_non_eda_scope_requires_manual_review_without_accept_or_deny(tmp_path: Path) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "llm2_non_eda_scope_gate.db")
    session_factory = create_session_factory(async_url)

    case_repo = SqlAlchemyCaseRepository(session_factory)
    queue_repo = SqlAlchemyJobQueueRepository(session_factory)
    audit_repo = SqlAlchemyAuditRepository(session_factory)

    case = await case_repo.create_case(
        CaseCreateInput(
            case_id=uuid4(),
            status=CaseStatus.R1_ACK_PROCESSING,
            room1_origin_room_id="!room1:example.org",
            room1_origin_event_id="$origin-llm2-scope-non-eda",
            room1_sender_user_id="@human:example.org",
        )
    )

    llm1_service = Llm1Service(
        llm_client=FakeLlmClient(
            json.dumps(_llm1_payload_with_exam_type("12345", exam_type="non_eda"))
        )
    )
    llm2_client = FakeLlmClient(json.dumps(_valid_llm2_payload(str(case.case_id), "12345")))
    llm2_service = Llm2Service(llm_client=llm2_client)

    service = ProcessPdfCaseService(
        case_repository=case_repo,
        mxc_downloader=MatrixMxcDownloader(
            FakeMatrixMediaClient(
                _build_simple_pdf(
                    "RELATORIO DE OCORRENCIAS 12345 " "clinical text 12345"
                )
            )
        ),
        text_extractor=PdfTextExtractor(),
        llm1_service=llm1_service,
        llm2_service=llm2_service,
        audit_repository=audit_repo,
        job_queue=queue_repo,
    )

    await service.process_case(case_id=case.case_id, pdf_mxc_url="mxc://example.org/pdf")

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        row = connection.execute(
            sa.text("SELECT suggested_action_json FROM cases WHERE case_id = :case_id"),
            {"case_id": case.case_id.hex},
        ).mappings().one()
        room2_jobs = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM jobs "
                "WHERE case_id = :case_id AND job_type = 'post_room2_widget'"
            ),
            {"case_id": case.case_id.hex},
        ).scalar_one()
        room1_manual_review_jobs = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM jobs "
                "WHERE case_id = :case_id "
                "AND job_type = 'post_room1_final_scope_manual_review'"
            ),
            {"case_id": case.case_id.hex},
        ).scalar_one()
        scope_gate_audit_payload_raw = connection.execute(
            sa.text(
                "SELECT payload FROM case_events "
                "WHERE case_id = :case_id "
                "AND event_type = 'EDA_SCOPE_GATED_MANUAL_REVIEW' "
                "ORDER BY id DESC LIMIT 1"
            ),
            {"case_id": case.case_id.hex},
        ).scalar_one()

    suggested_action = _decode_json(row["suggested_action_json"])
    scope_gate_audit_payload = _decode_json(scope_gate_audit_payload_raw)

    assert suggested_action.get("decision") == "manual_review_required"
    assert suggested_action.get("suggestion") not in {"accept", "deny"}
    _assert_preop_gate_contract(
        suggested_action,
        expected_decision="manual_review_required",
    )
    preop_gate = suggested_action["preop_gate"]
    assert isinstance(preop_gate, dict)
    assert preop_gate.get("decision") == suggested_action.get("decision")
    assert int(room2_jobs) == 0
    assert int(room1_manual_review_jobs) == 1
    assert scope_gate_audit_payload["reason_code"] == "non_eda_request"
    assert scope_gate_audit_payload["reason_text"]
    assert scope_gate_audit_payload["evidence_spans"] == [
        {
            "field_path": "preop_screening.exam_type",
            "excerpt": "solicitacao classificada como non_eda",
        }
    ]
    assert len(llm2_client.calls) == 0


@pytest.mark.asyncio
async def test_unknown_scope_requires_manual_review_without_accept_or_deny(tmp_path: Path) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "llm2_unknown_scope_gate.db")
    session_factory = create_session_factory(async_url)

    case_repo = SqlAlchemyCaseRepository(session_factory)
    queue_repo = SqlAlchemyJobQueueRepository(session_factory)
    audit_repo = SqlAlchemyAuditRepository(session_factory)

    case = await case_repo.create_case(
        CaseCreateInput(
            case_id=uuid4(),
            status=CaseStatus.R1_ACK_PROCESSING,
            room1_origin_room_id="!room1:example.org",
            room1_origin_event_id="$origin-llm2-scope-unknown",
            room1_sender_user_id="@human:example.org",
        )
    )

    llm1_service = Llm1Service(
        llm_client=FakeLlmClient(
            json.dumps(_llm1_payload_with_exam_type("12345", exam_type="unknown"))
        )
    )
    llm2_client = FakeLlmClient(json.dumps(_valid_llm2_payload(str(case.case_id), "12345")))
    llm2_service = Llm2Service(llm_client=llm2_client)

    service = ProcessPdfCaseService(
        case_repository=case_repo,
        mxc_downloader=MatrixMxcDownloader(
            FakeMatrixMediaClient(
                _build_simple_pdf(
                    "RELATORIO DE OCORRENCIAS 12345 " "clinical text 12345"
                )
            )
        ),
        text_extractor=PdfTextExtractor(),
        llm1_service=llm1_service,
        llm2_service=llm2_service,
        audit_repository=audit_repo,
        job_queue=queue_repo,
    )

    await service.process_case(case_id=case.case_id, pdf_mxc_url="mxc://example.org/pdf")

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        row = connection.execute(
            sa.text("SELECT suggested_action_json FROM cases WHERE case_id = :case_id"),
            {"case_id": case.case_id.hex},
        ).mappings().one()
        room2_jobs = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM jobs "
                "WHERE case_id = :case_id AND job_type = 'post_room2_widget'"
            ),
            {"case_id": case.case_id.hex},
        ).scalar_one()
        room1_manual_review_jobs = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM jobs "
                "WHERE case_id = :case_id "
                "AND job_type = 'post_room1_final_scope_manual_review'"
            ),
            {"case_id": case.case_id.hex},
        ).scalar_one()
        scope_gate_audit_payload_raw = connection.execute(
            sa.text(
                "SELECT payload FROM case_events "
                "WHERE case_id = :case_id "
                "AND event_type = 'EDA_SCOPE_GATED_MANUAL_REVIEW' "
                "ORDER BY id DESC LIMIT 1"
            ),
            {"case_id": case.case_id.hex},
        ).scalar_one()

    suggested_action = _decode_json(row["suggested_action_json"])
    scope_gate_audit_payload = _decode_json(scope_gate_audit_payload_raw)

    assert suggested_action.get("decision") == "manual_review_required"
    assert suggested_action.get("suggestion") not in {"accept", "deny"}
    assert int(room2_jobs) == 0
    assert int(room1_manual_review_jobs) == 1
    assert scope_gate_audit_payload["reason_code"] == "unknown_exam_type"
    assert scope_gate_audit_payload["reason_text"]
    assert scope_gate_audit_payload["evidence_spans"] == [
        {
            "field_path": "preop_screening.exam_type",
            "excerpt": "solicitacao classificada como unknown",
        }
    ]
    assert len(llm2_client.calls) == 0


@pytest.mark.asyncio
async def test_unknown_scope_with_explicit_eda_request_continues_to_llm2(
    tmp_path: Path,
) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "llm2_unknown_scope_explicit_eda.db")
    session_factory = create_session_factory(async_url)

    case_repo = SqlAlchemyCaseRepository(session_factory)
    queue_repo = SqlAlchemyJobQueueRepository(session_factory)
    audit_repo = SqlAlchemyAuditRepository(session_factory)

    case = await case_repo.create_case(
        CaseCreateInput(
            case_id=uuid4(),
            status=CaseStatus.R1_ACK_PROCESSING,
            room1_origin_room_id="!room1:example.org",
            room1_origin_event_id="$origin-llm2-scope-unknown-explicit-eda",
            room1_sender_user_id="@human:example.org",
        )
    )

    llm1_service = Llm1Service(
        llm_client=FakeLlmClient(
            json.dumps(_llm1_payload_with_exam_type("12345", exam_type="unknown"))
        )
    )
    llm2_client = FakeLlmClient(json.dumps(_valid_llm2_payload(str(case.case_id), "12345")))
    llm2_service = Llm2Service(llm_client=llm2_client)

    service = ProcessPdfCaseService(
        case_repository=case_repo,
        mxc_downloader=MatrixMxcDownloader(
            FakeMatrixMediaClient(
                _build_simple_pdf(
                    "RELATORIO DE OCORRENCIAS 12345 "
                    "Motivo da Solicitacao: Endoscopia Digestiva Alta - EDA"
                )
            )
        ),
        text_extractor=PdfTextExtractor(),
        llm1_service=llm1_service,
        llm2_service=llm2_service,
        audit_repository=audit_repo,
        job_queue=queue_repo,
    )

    await service.process_case(case_id=case.case_id, pdf_mxc_url="mxc://example.org/pdf")

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        row = connection.execute(
            sa.text("SELECT suggested_action_json FROM cases WHERE case_id = :case_id"),
            {"case_id": case.case_id.hex},
        ).mappings().one()
        room2_jobs = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM jobs "
                "WHERE case_id = :case_id AND job_type = 'post_room2_widget'"
            ),
            {"case_id": case.case_id.hex},
        ).scalar_one()
        room1_manual_review_jobs = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM jobs "
                "WHERE case_id = :case_id "
                "AND job_type = 'post_room1_final_scope_manual_review'"
            ),
            {"case_id": case.case_id.hex},
        ).scalar_one()

    suggested_action = _decode_json(row["suggested_action_json"])
    assert suggested_action.get("suggestion") == "accept"
    assert int(room2_jobs) == 1
    assert int(room1_manual_review_jobs) == 0
    assert len(llm2_client.calls) == 1


@pytest.mark.asyncio
async def test_unknown_scope_with_explicit_dotted_eda_abbreviation_continues_to_llm2(
    tmp_path: Path,
) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "llm2_unknown_scope_dotted_eda.db")
    session_factory = create_session_factory(async_url)

    case_repo = SqlAlchemyCaseRepository(session_factory)
    queue_repo = SqlAlchemyJobQueueRepository(session_factory)

    case = await case_repo.create_case(
        CaseCreateInput(
            case_id=uuid4(),
            status=CaseStatus.R1_ACK_PROCESSING,
            room1_origin_room_id="!room1:example.org",
            room1_origin_event_id="$origin-llm2-scope-unknown-dotted-eda",
            room1_sender_user_id="@human:example.org",
        )
    )

    llm1_service = Llm1Service(
        llm_client=FakeLlmClient(
            json.dumps(_llm1_payload_with_exam_type("12345", exam_type="unknown"))
        )
    )
    llm2_client = FakeLlmClient(json.dumps(_valid_llm2_payload(str(case.case_id), "12345")))

    service = ProcessPdfCaseService(
        case_repository=case_repo,
        mxc_downloader=MatrixMxcDownloader(
            FakeMatrixMediaClient(
                _build_simple_pdf(
                    "RELATORIO DE OCORRENCIAS 12345 "
                    "Motivo da Solicitacao: E.D.A"
                )
            )
        ),
        text_extractor=PdfTextExtractor(),
        llm1_service=llm1_service,
        llm2_service=Llm2Service(llm_client=llm2_client),
        job_queue=queue_repo,
    )

    await service.process_case(case_id=case.case_id, pdf_mxc_url="mxc://example.org/pdf")

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        row = connection.execute(
            sa.text("SELECT suggested_action_json FROM cases WHERE case_id = :case_id"),
            {"case_id": case.case_id.hex},
        ).mappings().one()
        room2_jobs = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM jobs "
                "WHERE case_id = :case_id AND job_type = 'post_room2_widget'"
            ),
            {"case_id": case.case_id.hex},
        ).scalar_one()
        room1_manual_review_jobs = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM jobs "
                "WHERE case_id = :case_id "
                "AND job_type = 'post_room1_final_scope_manual_review'"
            ),
            {"case_id": case.case_id.hex},
        ).scalar_one()

    suggested_action = _decode_json(row["suggested_action_json"])
    assert suggested_action.get("suggestion") == "accept"
    assert int(room2_jobs) == 1
    assert int(room1_manual_review_jobs) == 0
    assert len(llm2_client.calls) == 1


@pytest.mark.asyncio
async def test_unknown_scope_with_videoendoscopia_evidence_span_continues_to_llm2(
    tmp_path: Path,
) -> None:
    sync_url, async_url = _upgrade_head(
        tmp_path,
        "llm2_unknown_scope_videoendoscopia_evidence.db",
    )
    session_factory = create_session_factory(async_url)

    case_repo = SqlAlchemyCaseRepository(session_factory)
    queue_repo = SqlAlchemyJobQueueRepository(session_factory)

    case = await case_repo.create_case(
        CaseCreateInput(
            case_id=uuid4(),
            status=CaseStatus.R1_ACK_PROCESSING,
            room1_origin_room_id="!room1:example.org",
            room1_origin_event_id="$origin-llm2-scope-unknown-videoendoscopia-evidence",
            room1_sender_user_id="@human:example.org",
        )
    )

    llm1_service = Llm1Service(
        llm_client=FakeLlmClient(
            json.dumps(
                _llm1_payload_with_exam_type(
                    "12345",
                    exam_type="unknown",
                    evidence_excerpt=(
                        "Motivo da Solicitacao: Videoendoscopia Digestiva Alta"
                    ),
                )
            )
        )
    )
    llm2_client = FakeLlmClient(json.dumps(_valid_llm2_payload(str(case.case_id), "12345")))

    service = ProcessPdfCaseService(
        case_repository=case_repo,
        mxc_downloader=MatrixMxcDownloader(
            FakeMatrixMediaClient(
                _build_simple_pdf("RELATORIO DE OCORRENCIAS 12345 texto clinico")
            )
        ),
        text_extractor=PdfTextExtractor(),
        llm1_service=llm1_service,
        llm2_service=Llm2Service(llm_client=llm2_client),
        job_queue=queue_repo,
    )

    await service.process_case(case_id=case.case_id, pdf_mxc_url="mxc://example.org/pdf")

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        row = connection.execute(
            sa.text("SELECT suggested_action_json FROM cases WHERE case_id = :case_id"),
            {"case_id": case.case_id.hex},
        ).mappings().one()
        room2_jobs = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM jobs "
                "WHERE case_id = :case_id AND job_type = 'post_room2_widget'"
            ),
            {"case_id": case.case_id.hex},
        ).scalar_one()
        room1_manual_review_jobs = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM jobs "
                "WHERE case_id = :case_id "
                "AND job_type = 'post_room1_final_scope_manual_review'"
            ),
            {"case_id": case.case_id.hex},
        ).scalar_one()

    suggested_action = _decode_json(row["suggested_action_json"])
    assert suggested_action.get("suggestion") == "accept"
    assert int(room2_jobs) == 1
    assert int(room1_manual_review_jobs) == 0
    assert len(llm2_client.calls) == 1


@pytest.mark.asyncio
async def test_scope_gate_keeps_gtt_keyword_inside_supported_eda_flow(
    tmp_path: Path,
) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "llm2_scope_gate_gtt_keyword.db")
    session_factory = create_session_factory(async_url)

    case_repo = SqlAlchemyCaseRepository(session_factory)
    queue_repo = SqlAlchemyJobQueueRepository(session_factory)
    audit_repo = SqlAlchemyAuditRepository(session_factory)

    case = await case_repo.create_case(
        CaseCreateInput(
            case_id=uuid4(),
            status=CaseStatus.R1_ACK_PROCESSING,
            room1_origin_room_id="!room1:example.org",
            room1_origin_event_id="$origin-llm2-scope-gtt-keyword",
            room1_sender_user_id="@human:example.org",
        )
    )

    llm1_payload = _valid_llm1_payload("12345")
    llm2_client = FakeLlmClient(json.dumps(_valid_llm2_payload(str(case.case_id), "12345")))

    service = ProcessPdfCaseService(
        case_repository=case_repo,
        mxc_downloader=MatrixMxcDownloader(
            FakeMatrixMediaClient(
                _build_simple_pdf(
                    "RELATORIO DE OCORRENCIAS 12345 "
                    "SOLICITO CONFECCAO DE GTT VIA ENDOSCOPICA"
                )
            )
        ),
        text_extractor=PdfTextExtractor(),
        llm1_service=Llm1Service(llm_client=FakeLlmClient(json.dumps(llm1_payload))),
        llm2_service=Llm2Service(llm_client=llm2_client),
        audit_repository=audit_repo,
        job_queue=queue_repo,
    )

    await service.process_case(case_id=case.case_id, pdf_mxc_url="mxc://example.org/pdf")

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        row = connection.execute(
            sa.text("SELECT suggested_action_json FROM cases WHERE case_id = :case_id"),
            {"case_id": case.case_id.hex},
        ).mappings().one()
        room2_jobs = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM jobs "
                "WHERE case_id = :case_id AND job_type = 'post_room2_widget'"
            ),
            {"case_id": case.case_id.hex},
        ).scalar_one()
        room1_manual_review_jobs = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM jobs "
                "WHERE case_id = :case_id "
                "AND job_type = 'post_room1_final_scope_manual_review'"
            ),
            {"case_id": case.case_id.hex},
        ).scalar_one()

    suggested_action = _decode_json(row["suggested_action_json"])
    assert suggested_action.get("suggestion") == "accept"
    assert int(room2_jobs) == 1
    assert int(room1_manual_review_jobs) == 0
    assert len(llm2_client.calls) == 1


@pytest.mark.asyncio
async def test_scope_gate_keeps_esophageal_dilation_keyword_inside_supported_eda_flow(
    tmp_path: Path,
) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "llm2_scope_gate_dilation_keyword.db")
    session_factory = create_session_factory(async_url)

    case_repo = SqlAlchemyCaseRepository(session_factory)
    queue_repo = SqlAlchemyJobQueueRepository(session_factory)
    audit_repo = SqlAlchemyAuditRepository(session_factory)

    case = await case_repo.create_case(
        CaseCreateInput(
            case_id=uuid4(),
            status=CaseStatus.R1_ACK_PROCESSING,
            room1_origin_room_id="!room1:example.org",
            room1_origin_event_id="$origin-llm2-scope-dilation-keyword",
            room1_sender_user_id="@human:example.org",
        )
    )

    llm1_payload = _valid_llm1_payload("12345")
    llm2_client = FakeLlmClient(json.dumps(_valid_llm2_payload(str(case.case_id), "12345")))

    service = ProcessPdfCaseService(
        case_repository=case_repo,
        mxc_downloader=MatrixMxcDownloader(
            FakeMatrixMediaClient(
                _build_simple_pdf(
                    "RELATORIO DE OCORRENCIAS 12345 "
                    "PACIENTE COM INDICACAO DE DILATACAO ESOFAGICA"
                )
            )
        ),
        text_extractor=PdfTextExtractor(),
        llm1_service=Llm1Service(llm_client=FakeLlmClient(json.dumps(llm1_payload))),
        llm2_service=Llm2Service(llm_client=llm2_client),
        audit_repository=audit_repo,
        job_queue=queue_repo,
    )

    await service.process_case(case_id=case.case_id, pdf_mxc_url="mxc://example.org/pdf")

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        row = connection.execute(
            sa.text("SELECT suggested_action_json FROM cases WHERE case_id = :case_id"),
            {"case_id": case.case_id.hex},
        ).mappings().one()
        room2_jobs = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM jobs "
                "WHERE case_id = :case_id AND job_type = 'post_room2_widget'"
            ),
            {"case_id": case.case_id.hex},
        ).scalar_one()
        room1_manual_review_jobs = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM jobs "
                "WHERE case_id = :case_id "
                "AND job_type = 'post_room1_final_scope_manual_review'"
            ),
            {"case_id": case.case_id.hex},
        ).scalar_one()

    suggested_action = _decode_json(row["suggested_action_json"])
    assert suggested_action.get("suggestion") == "accept"
    assert int(room2_jobs) == 1
    assert int(room1_manual_review_jobs) == 0
    assert len(llm2_client.calls) == 1


@pytest.mark.asyncio
async def test_unknown_scope_with_foreign_body_keyword_continues_to_llm2(
    tmp_path: Path,
) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "llm2_unknown_scope_foreign_body.db")
    session_factory = create_session_factory(async_url)

    case_repo = SqlAlchemyCaseRepository(session_factory)
    queue_repo = SqlAlchemyJobQueueRepository(session_factory)

    case = await case_repo.create_case(
        CaseCreateInput(
            case_id=uuid4(),
            status=CaseStatus.R1_ACK_PROCESSING,
            room1_origin_room_id="!room1:example.org",
            room1_origin_event_id="$origin-llm2-scope-unknown-foreign-body",
            room1_sender_user_id="@human:example.org",
        )
    )

    llm1_service = Llm1Service(
        llm_client=FakeLlmClient(
            json.dumps(_llm1_payload_with_exam_type("12345", exam_type="unknown"))
        )
    )
    llm2_client = FakeLlmClient(json.dumps(_valid_llm2_payload(str(case.case_id), "12345")))

    service = ProcessPdfCaseService(
        case_repository=case_repo,
        mxc_downloader=MatrixMxcDownloader(
            FakeMatrixMediaClient(
                _build_simple_pdf(
                    "RELATORIO DE OCORRENCIAS 12345 "
                    "EDA para retirada de corpo estranho esofagico"
                )
            )
        ),
        text_extractor=PdfTextExtractor(),
        llm1_service=llm1_service,
        llm2_service=Llm2Service(llm_client=llm2_client),
        job_queue=queue_repo,
    )

    await service.process_case(case_id=case.case_id, pdf_mxc_url="mxc://example.org/pdf")

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        row = connection.execute(
            sa.text("SELECT suggested_action_json FROM cases WHERE case_id = :case_id"),
            {"case_id": case.case_id.hex},
        ).mappings().one()
        room2_jobs = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM jobs "
                "WHERE case_id = :case_id AND job_type = 'post_room2_widget'"
            ),
            {"case_id": case.case_id.hex},
        ).scalar_one()
        room1_manual_review_jobs = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM jobs "
                "WHERE case_id = :case_id "
                "AND job_type = 'post_room1_final_scope_manual_review'"
            ),
            {"case_id": case.case_id.hex},
        ).scalar_one()

    suggested_action = _decode_json(row["suggested_action_json"])
    assert suggested_action.get("suggestion") == "accept"
    assert int(room2_jobs) == 1
    assert int(room1_manual_review_jobs) == 0
    assert len(llm2_client.calls) == 1


@pytest.mark.asyncio
async def test_supported_gastrostomy_subtype_from_llm1_payload_skips_scope_manual_review(
    tmp_path: Path,
) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "llm2_scope_gastrostomy_subtype.db")
    session_factory = create_session_factory(async_url)

    case_repo = SqlAlchemyCaseRepository(session_factory)
    queue_repo = SqlAlchemyJobQueueRepository(session_factory)

    case = await case_repo.create_case(
        CaseCreateInput(
            case_id=uuid4(),
            status=CaseStatus.R1_ACK_PROCESSING,
            room1_origin_room_id="!room1:example.org",
            room1_origin_event_id="$origin-llm2-scope-gastrostomy-subtype",
            room1_sender_user_id="@human:example.org",
        )
    )

    llm1_payload = _llm1_payload_with_exam_type("12345", exam_type="unknown")
    eda = llm1_payload["eda"]
    assert isinstance(eda, dict)
    requested_procedure = eda["requested_procedure"]
    assert isinstance(requested_procedure, dict)
    requested_procedure["subtype"] = "gastrostomy"
    requested_procedure["name"] = "EDA para gastrostomia"
    preop_screening = llm1_payload["preop_screening"]
    assert isinstance(preop_screening, dict)
    rulebook_signals = preop_screening["rulebook_signals"]
    assert isinstance(rulebook_signals, dict)
    rulebook_signals["eda_subtype"] = "gastrostomy"

    llm2_client = FakeLlmClient(json.dumps(_valid_llm2_payload(str(case.case_id), "12345")))

    service = ProcessPdfCaseService(
        case_repository=case_repo,
        mxc_downloader=MatrixMxcDownloader(
            FakeMatrixMediaClient(_build_simple_pdf("RELATORIO DE OCORRENCIAS 12345 texto"))
        ),
        text_extractor=PdfTextExtractor(),
        llm1_service=Llm1Service(llm_client=FakeLlmClient(json.dumps(llm1_payload))),
        llm2_service=Llm2Service(llm_client=llm2_client),
        job_queue=queue_repo,
    )

    await service.process_case(case_id=case.case_id, pdf_mxc_url="mxc://example.org/pdf")

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        room2_jobs = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM jobs "
                "WHERE case_id = :case_id AND job_type = 'post_room2_widget'"
            ),
            {"case_id": case.case_id.hex},
        ).scalar_one()
        room1_manual_review_jobs = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM jobs "
                "WHERE case_id = :case_id "
                "AND job_type = 'post_room1_final_scope_manual_review'"
            ),
            {"case_id": case.case_id.hex},
        ).scalar_one()

    assert int(room2_jobs) == 1
    assert int(room1_manual_review_jobs) == 0
    assert len(llm2_client.calls) == 1


@pytest.mark.asyncio
async def test_legacy_precheck_flags_do_not_force_persisted_deny_after_rulebook_rewrite(
    tmp_path: Path,
) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "llm2_legacy_precheck_no_force.db")
    session_factory = create_session_factory(async_url)

    case_repo = SqlAlchemyCaseRepository(session_factory)
    queue_repo = SqlAlchemyJobQueueRepository(session_factory)
    audit_repo = SqlAlchemyAuditRepository(session_factory)

    case = await case_repo.create_case(
        CaseCreateInput(
            case_id=uuid4(),
            status=CaseStatus.R1_ACK_PROCESSING,
            room1_origin_room_id="!room1:example.org",
            room1_origin_event_id="$origin-llm2-2",
            room1_sender_user_id="@human:example.org",
        )
    )

    llm1_payload = _valid_llm1_payload("12345")
    llm1_payload["policy_precheck"] = {
        "excluded_from_eda_flow": True,
        "exclusion_reason": "fora do fluxo",
        "labs_required": True,
        "labs_pass": "no",
        "labs_failed_items": ["hb"],
        "ecg_required": True,
        "ecg_present": "no",
        "pediatric_flag": False,
        "notes": None,
    }

    llm2_payload = _valid_llm2_payload(str(case.case_id), "12345")
    llm2_payload["suggestion"] = "accept"
    llm2_payload["policy_alignment"] = {
        "excluded_request": False,
        "labs_ok": "yes",
        "ecg_ok": "yes",
        "pediatric_flag": False,
        "notes": None,
    }

    llm1_service = Llm1Service(llm_client=FakeLlmClient(json.dumps(llm1_payload)))
    llm2_service = Llm2Service(llm_client=FakeLlmClient(json.dumps(llm2_payload)))

    service = ProcessPdfCaseService(
        case_repository=case_repo,
        mxc_downloader=MatrixMxcDownloader(
            FakeMatrixMediaClient(
                _build_simple_pdf(
                    "RELATORIO DE OCORRENCIAS 12345 " "clinical text 12345"
                )
            )
        ),
        text_extractor=PdfTextExtractor(),
        llm1_service=llm1_service,
        llm2_service=llm2_service,
        audit_repository=audit_repo,
        job_queue=queue_repo,
    )

    await service.process_case(case_id=case.case_id, pdf_mxc_url="mxc://example.org/pdf")

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        row = connection.execute(
            sa.text("SELECT suggested_action_json FROM cases ORDER BY created_at DESC LIMIT 1")
        ).mappings().one()
        contradiction_events = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM case_events "
                "WHERE event_type = 'LLM_CONTRADICTION_DETECTED'"
            )
        ).scalar_one()

    suggested_action = _decode_json(row["suggested_action_json"])

    assert suggested_action["suggestion"] == "accept"
    assert suggested_action["preop_gate"]["decision"] == "accept"
    assert suggested_action["policy_alignment"]["excluded_request"] is False
    assert contradiction_events == 0


@pytest.mark.asyncio
async def test_high_risk_asa_maps_persisted_support_to_anesthesist_icu(
    tmp_path: Path,
) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "llm2_support_mapping_high_risk.db")
    session_factory = create_session_factory(async_url)

    case_repo = SqlAlchemyCaseRepository(session_factory)
    queue_repo = SqlAlchemyJobQueueRepository(session_factory)

    case = await case_repo.create_case(
        CaseCreateInput(
            case_id=uuid4(),
            status=CaseStatus.R1_ACK_PROCESSING,
            room1_origin_room_id="!room1:example.org",
            room1_origin_event_id="$origin-llm2-support-high-risk",
            room1_sender_user_id="@human:example.org",
        )
    )

    llm1_payload = _valid_llm1_payload("12345")
    eda = llm1_payload["eda"]
    assert isinstance(eda, dict)
    asa = eda["asa"]
    assert isinstance(asa, dict)
    asa["bucket"] = "insufficient_data"
    cardiovascular_risk = eda["cardiovascular_risk"]
    assert isinstance(cardiovascular_risk, dict)
    cardiovascular_risk["level"] = "moderate_high"

    llm1_service = Llm1Service(llm_client=FakeLlmClient(json.dumps(llm1_payload)))
    llm2_payload = _valid_llm2_payload(str(case.case_id), "12345")
    llm2_payload["support_recommendation"] = "none"
    llm2_service = Llm2Service(llm_client=FakeLlmClient(json.dumps(llm2_payload)))

    service = ProcessPdfCaseService(
        case_repository=case_repo,
        mxc_downloader=MatrixMxcDownloader(
            FakeMatrixMediaClient(
                _build_simple_pdf(
                    "RELATORIO DE OCORRENCIAS 12345 " "clinical text 12345"
                )
            )
        ),
        text_extractor=PdfTextExtractor(),
        llm1_service=llm1_service,
        llm2_service=llm2_service,
        job_queue=queue_repo,
    )

    await service.process_case(case_id=case.case_id, pdf_mxc_url="mxc://example.org/pdf")

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        row = connection.execute(
            sa.text("SELECT suggested_action_json FROM cases ORDER BY created_at DESC LIMIT 1")
        ).mappings().one()

    suggested_action = _decode_json(row["suggested_action_json"])

    assert suggested_action["suggestion"] == "accept"
    assert suggested_action["support_recommendation"] == "anesthesist_icu"
    asa_payload = suggested_action.get("asa")
    assert isinstance(asa_payload, dict)
    assert asa_payload.get("bucket") == "insufficient_data"
    assert (
        asa_payload.get("display_text")
        == "não foi possível estimar com os dados apresentados"
    )


@pytest.mark.asyncio
async def test_deterministic_preop_gate_deny_overrides_llm2_accept_for_persisted_suggestion(
    tmp_path: Path,
) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "llm2_preop_gate_override.db")
    session_factory = create_session_factory(async_url)

    case_repo = SqlAlchemyCaseRepository(session_factory)
    queue_repo = SqlAlchemyJobQueueRepository(session_factory)

    case = await case_repo.create_case(
        CaseCreateInput(
            case_id=uuid4(),
            status=CaseStatus.R1_ACK_PROCESSING,
            room1_origin_room_id="!room1:example.org",
            room1_origin_event_id="$origin-llm2-preop-override",
            room1_sender_user_id="@human:example.org",
        )
    )

    llm1_payload = _valid_llm1_payload("12345")
    eda = llm1_payload["eda"]
    assert isinstance(eda, dict)
    labs = eda["labs"]
    assert isinstance(labs, dict)
    labs["creatinine_mg_dl"] = None
    preop_screening = llm1_payload["preop_screening"]
    assert isinstance(preop_screening, dict)
    rulebook_signals = preop_screening["rulebook_signals"]
    assert isinstance(rulebook_signals, dict)
    minimum_exam_evidence = rulebook_signals["minimum_exam_evidence"]
    assert isinstance(minimum_exam_evidence, dict)
    minimum_exam_evidence["creatinine_present"] = "no"

    llm1_service = Llm1Service(llm_client=FakeLlmClient(json.dumps(llm1_payload)))
    llm2_service = Llm2Service(
        llm_client=FakeLlmClient(json.dumps(_valid_llm2_payload(str(case.case_id), "12345")))
    )

    service = ProcessPdfCaseService(
        case_repository=case_repo,
        mxc_downloader=MatrixMxcDownloader(
            FakeMatrixMediaClient(
                _build_simple_pdf(
                    "RELATORIO DE OCORRENCIAS 12345 " "clinical text 12345"
                )
            )
        ),
        text_extractor=PdfTextExtractor(),
        llm1_service=llm1_service,
        llm2_service=llm2_service,
        job_queue=queue_repo,
    )

    await service.process_case(case_id=case.case_id, pdf_mxc_url="mxc://example.org/pdf")

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        row = connection.execute(
            sa.text("SELECT suggested_action_json FROM cases ORDER BY created_at DESC LIMIT 1")
        ).mappings().one()

    suggested_action = _decode_json(row["suggested_action_json"])

    assert suggested_action["suggestion"] == "deny"
    assert suggested_action["decision"] == "deny"
    assert suggested_action["reason_code"] == "missing_minimum_exam_creatinine"
    assert suggested_action["preop_gate"]["decision"] == "deny"


@pytest.mark.asyncio
async def test_runtime_provider_adapter_preserves_llm2_retriable_mapping(
    tmp_path: Path,
) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "llm2_provider_non_json.db")
    session_factory = create_session_factory(async_url)

    case_repo = SqlAlchemyCaseRepository(session_factory)
    queue_repo = SqlAlchemyJobQueueRepository(session_factory)

    case = await case_repo.create_case(
        CaseCreateInput(
            case_id=uuid4(),
            status=CaseStatus.R1_ACK_PROCESSING,
            room1_origin_room_id="!room1:example.org",
            room1_origin_event_id="$origin-llm2-provider-1",
            room1_sender_user_id="@human:example.org",
        )
    )

    llm1_payload: dict[str, object] = {
        "choices": [{"message": {"content": json.dumps(_valid_llm1_payload("12345"))}}]
    }
    llm2_payload: dict[str, object] = {
        "choices": [{"message": {"content": "not-json"}}]
    }

    llm1_service = Llm1Service(
        llm_client=OpenAiChatCompletionsClient(
            api_key="sk-test",
            model="gpt-4o-mini",
            transport=FakeOpenAiTransport([llm1_payload]),
        )
    )
    llm2_service = Llm2Service(
        llm_client=OpenAiChatCompletionsClient(
            api_key="sk-test",
            model="gpt-4o-mini",
            transport=FakeOpenAiTransport([llm2_payload]),
        )
    )

    service = ProcessPdfCaseService(
        case_repository=case_repo,
        mxc_downloader=MatrixMxcDownloader(
            FakeMatrixMediaClient(
                _build_simple_pdf(
                    "RELATORIO DE OCORRENCIAS 12345 " "clinical text 12345"
                )
            )
        ),
        text_extractor=PdfTextExtractor(),
        llm1_service=llm1_service,
        llm2_service=llm2_service,
        job_queue=queue_repo,
    )

    with pytest.raises(ProcessPdfCaseRetriableError) as error_info:
        await service.process_case(case_id=case.case_id, pdf_mxc_url="mxc://example.org/pdf")

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        interaction_rows = connection.execute(
            sa.text(
                "SELECT stage, model_name, output_payload "
                "FROM case_llm_interactions "
                "WHERE case_id = :case_id "
                "ORDER BY id"
            ),
            {"case_id": case.case_id.hex},
        ).mappings().all()

    assert error_info.value.cause == "llm2"
    assert "LLM2 returned non-JSON payload" in error_info.value.details
    assert len(interaction_rows) == 2
    assert interaction_rows[0]["stage"] == "LLM1"
    assert interaction_rows[0]["model_name"] == "gpt-4o-mini"
    assert interaction_rows[1]["stage"] == "LLM2"
    assert interaction_rows[1]["model_name"] == "gpt-4o-mini"
    assert _decode_json(interaction_rows[1]["output_payload"])["raw_response"] == "not-json"
