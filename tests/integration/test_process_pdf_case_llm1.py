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
from triage_automation.application.services.process_pdf_case_service import (
    ProcessPdfCaseRetriableError,
    ProcessPdfCaseService,
)
from triage_automation.domain.case_status import CaseStatus
from triage_automation.infrastructure.db.case_repository import SqlAlchemyCaseRepository
from triage_automation.infrastructure.db.session import create_session_factory
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

    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        return self._response_text


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


def _decode_json(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        parsed = json.loads(value)
        assert isinstance(parsed, dict)
        return parsed
    assert isinstance(value, dict)
    return value


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
            "ecg": {"report_present": "yes", "abnormal_flag": "no", "source_text_hint": None},
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
            "evidence_spans": [
                {
                    "field_path": "preop_screening.has_ecg_report",
                    "excerpt": "ECG com laudo anexado",
                }
            ],
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
                    "chest_xray_required": "no",
                    "echocardiogram_required": "no",
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


@pytest.mark.asyncio
async def test_valid_llm1_response_persists_structured_data_and_summary(tmp_path: Path) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "llm1_ok.db")
    session_factory = create_session_factory(async_url)
    case_repo = SqlAlchemyCaseRepository(session_factory)

    case = await case_repo.create_case(
        CaseCreateInput(
            case_id=uuid4(),
            status=CaseStatus.R1_ACK_PROCESSING,
            room1_origin_room_id="!room1:example.org",
            room1_origin_event_id="$origin-llm1-1",
            room1_sender_user_id="@human:example.org",
        )
    )

    llm1_service = Llm1Service(
        llm_client=FakeLlmClient(json.dumps(_valid_llm1_payload("12345")))
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
    )

    cleaned = await service.process_case(case_id=case.case_id, pdf_mxc_url="mxc://example.org/pdf")

    assert cleaned == "RELATORIO DE OCORRENCIAS clinical text"

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        row = connection.execute(
            sa.text(
                "SELECT status, structured_data_json, summary_text "
                "FROM cases ORDER BY created_at DESC LIMIT 1"
            )
        ).mappings().one()

    assert row["status"] == "LLM_STRUCT"
    assert row["structured_data_json"] is not None
    structured_data = _decode_json(row["structured_data_json"])
    assert structured_data["preop_screening"]["exam_type"] == "eda"
    assert structured_data["eda"]["requested_procedure"]["subtype"] == "standard"
    assert structured_data["eda"]["asa"]["bucket"] == "I-II"
    assert structured_data["preop_screening"]["rulebook_signals"]["eda_subtype"] == "standard"
    assert structured_data["preop_screening"]["has_ecg_report"] == "yes"
    assert structured_data["preop_screening"]["evidence_spans"] == [
        {
            "field_path": "preop_screening.has_ecg_report",
            "excerpt": "ECG com laudo anexado",
        }
    ]
    assert row["summary_text"] == "Resumo LLM1"


@pytest.mark.asyncio
async def test_process_pdf_case_persists_supported_subtype_and_insufficient_asa_payload(
    tmp_path: Path,
) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "llm1_supported_subtype_and_asa.db")
    session_factory = create_session_factory(async_url)
    case_repo = SqlAlchemyCaseRepository(session_factory)

    case = await case_repo.create_case(
        CaseCreateInput(
            case_id=uuid4(),
            status=CaseStatus.R1_ACK_PROCESSING,
            room1_origin_room_id="!room1:example.org",
            room1_origin_event_id="$origin-llm1-1b",
            room1_sender_user_id="@human:example.org",
        )
    )

    payload = _valid_llm1_payload("12345")
    payload["patient"]["age"] = 14
    payload["eda"]["is_pediatric"] = True
    payload["eda"]["requested_procedure"]["subtype"] = "gastrostomy"
    payload["eda"]["requested_procedure"]["name"] = "EDA para gastrostomia"
    payload["eda"]["asa"] = {
        "bucket": "insufficient_data",
        "source_text_hint": "dados limitados para estimativa pratica",
    }
    payload["eda"]["cardiovascular_risk"] = {
        "level": "unknown",
        "source_text_hint": "risco cardiovascular nao conclusivo",
    }
    payload["preop_screening"]["rulebook_signals"]["eda_subtype"] = "gastrostomy"
    payload["policy_precheck"]["pediatric_flag"] = True

    llm1_service = Llm1Service(llm_client=FakeLlmClient(json.dumps(payload)))
    service = ProcessPdfCaseService(
        case_repository=case_repo,
        mxc_downloader=MatrixMxcDownloader(
            FakeMatrixMediaClient(
                _build_simple_pdf(
                    "RELATORIO DE OCORRENCIAS 12345 " "paciente 14 anos com gastrostomia"
                )
            )
        ),
        text_extractor=PdfTextExtractor(),
        llm1_service=llm1_service,
    )

    await service.process_case(case_id=case.case_id, pdf_mxc_url="mxc://example.org/pdf")

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        row = connection.execute(
            sa.text(
                "SELECT structured_data_json FROM cases ORDER BY created_at DESC LIMIT 1"
            )
        ).mappings().one()

    structured_data = _decode_json(row["structured_data_json"])
    assert structured_data["eda"]["requested_procedure"]["subtype"] == "gastrostomy"
    assert structured_data["eda"]["asa"]["bucket"] == "insufficient_data"
    assert structured_data["eda"]["cardiovascular_risk"]["level"] == "unknown"
    assert structured_data["preop_screening"]["rulebook_signals"]["eda_subtype"] == "gastrostomy"
    assert structured_data["policy_precheck"]["pediatric_flag"] is True


@pytest.mark.asyncio
async def test_invalid_llm1_schema_maps_to_retriable_llm1_error(tmp_path: Path) -> None:
    _, async_url = _upgrade_head(tmp_path, "llm1_schema_fail.db")
    session_factory = create_session_factory(async_url)
    case_repo = SqlAlchemyCaseRepository(session_factory)

    case = await case_repo.create_case(
        CaseCreateInput(
            case_id=uuid4(),
            status=CaseStatus.R1_ACK_PROCESSING,
            room1_origin_room_id="!room1:example.org",
            room1_origin_event_id="$origin-llm1-2",
            room1_sender_user_id="@human:example.org",
        )
    )

    llm1_service = Llm1Service(llm_client=FakeLlmClient(json.dumps({"schema_version": "1.1"})))
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
    )

    with pytest.raises(ProcessPdfCaseRetriableError) as exc_info:
        await service.process_case(case_id=case.case_id, pdf_mxc_url="mxc://example.org/pdf")

    assert exc_info.value.cause == "llm1"
