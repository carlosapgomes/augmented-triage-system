from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic.config import Config

from alembic import command
from triage_automation.application.ports.case_repository_port import CaseCreateInput
from triage_automation.application.services.post_room2_widget_service import PostRoom2WidgetService
from triage_automation.domain.case_status import CaseStatus
from triage_automation.infrastructure.db.audit_repository import SqlAlchemyAuditRepository
from triage_automation.infrastructure.db.case_repository import SqlAlchemyCaseRepository
from triage_automation.infrastructure.db.message_repository import SqlAlchemyMessageRepository
from triage_automation.infrastructure.db.prior_case_queries import SqlAlchemyPriorCaseQueries
from triage_automation.infrastructure.db.session import create_session_factory


class FakeMatrixPoster:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self._counter = 0

    async def send_text(self, *, room_id: str, body: str) -> str:
        self.calls.append((room_id, body))
        self._counter += 1
        return f"$room2-{self._counter}"


def _upgrade_head(tmp_path: Path, filename: str) -> tuple[str, str]:
    db_path = tmp_path / filename
    sync_url = f"sqlite+pysqlite:///{db_path}"
    async_url = f"sqlite+aiosqlite:///{db_path}"

    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(alembic_config, "head")

    return sync_url, async_url


def _structured_data(agency_record_number: str) -> dict[str, Any]:
    return {
        "schema_version": "1.1",
        "language": "pt-BR",
        "agency_record_number": agency_record_number,
        "patient": {"name": "Paciente", "age": 52, "sex": "F", "document_id": None},
        "eda": {
            "indication_category": "dyspepsia",
            "exclusion_type": "none",
            "is_pediatric": False,
            "foreign_body_suspected": False,
            "requested_procedure": {"name": "EDA", "urgency": "eletivo"},
            "labs": {
                "hb_g_dl": 10.5,
                "platelets_per_mm3": 130000,
                "inr": 1.2,
                "source_text_hint": None,
            },
            "ecg": {
                "report_present": "yes",
                "abnormal_flag": "no",
                "source_text_hint": None,
            },
            "asa": {"class": "II", "confidence": "media", "rationale": None},
            "cardiovascular_risk": {"level": "low", "confidence": "media", "rationale": None},
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


def _suggested_action(case_id: UUID, agency_record_number: str) -> dict[str, Any]:
    return {
        "schema_version": "1.1",
        "language": "pt-BR",
        "case_id": str(case_id),
        "agency_record_number": agency_record_number,
        "suggestion": "deny",
        "support_recommendation": "anesthesist",
        "rationale": {
            "short_reason": "Informacoes insuficientes",
            "details": ["d1", "d2"],
            "missing_info_questions": ["q1"],
        },
        "policy_alignment": {
            "excluded_request": False,
            "labs_ok": "unknown",
            "ecg_ok": "unknown",
            "pediatric_flag": False,
            "notes": None,
        },
        "confidence": "media",
    }


def _extract_payload_from_widget_body(body: str) -> dict[str, Any]:
    marker = "```json\n"
    start = body.index(marker) + len(marker)
    end = body.index("\n```", start)
    return json.loads(body[start:end])


@pytest.mark.asyncio
async def test_post_room2_widget_includes_prior_and_moves_to_wait_doctor(tmp_path: Path) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "post_room2_widget.db")
    session_factory = create_session_factory(async_url)

    case_repo = SqlAlchemyCaseRepository(session_factory)
    audit_repo = SqlAlchemyAuditRepository(session_factory)
    message_repo = SqlAlchemyMessageRepository(session_factory)
    prior_queries = SqlAlchemyPriorCaseQueries(session_factory)
    matrix_poster = FakeMatrixPoster()

    prior_case = await case_repo.create_case(
        CaseCreateInput(
            case_id=uuid4(),
            status=CaseStatus.DOCTOR_DENIED,
            room1_origin_room_id="!room1:example.org",
            room1_origin_event_id="$origin-prior",
            room1_sender_user_id="@human:example.org",
        )
    )
    await case_repo.store_pdf_extraction(
        case_id=prior_case.case_id,
        pdf_mxc_url="mxc://example.org/prior",
        extracted_text="prior text",
        agency_record_number="12345",
    )

    now = datetime.now(tz=UTC)
    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "UPDATE cases SET created_at = :created_at, doctor_decision = 'deny', "
                "doctor_reason = 'prior denial', doctor_decided_at = :decided_at "
                "WHERE case_id = :case_id"
            ),
            {
                "created_at": now - timedelta(days=2),
                "decided_at": now - timedelta(days=2),
                "case_id": prior_case.case_id.hex,
            },
        )

    current_case = await case_repo.create_case(
        CaseCreateInput(
            case_id=uuid4(),
            status=CaseStatus.LLM_SUGGEST,
            room1_origin_room_id="!room1:example.org",
            room1_origin_event_id="$origin-current",
            room1_sender_user_id="@human:example.org",
        )
    )
    await case_repo.store_pdf_extraction(
        case_id=current_case.case_id,
        pdf_mxc_url="mxc://example.org/current",
        extracted_text="current text",
        agency_record_number="12345",
    )
    await case_repo.store_llm1_artifacts(
        case_id=current_case.case_id,
        structured_data_json=_structured_data("12345"),
        summary_text="Resumo LLM1",
    )
    await case_repo.store_llm2_artifacts(
        case_id=current_case.case_id,
        suggested_action_json=_suggested_action(current_case.case_id, "12345"),
    )

    service = PostRoom2WidgetService(
        room2_id="!room2:example.org",
        case_repository=case_repo,
        audit_repository=audit_repo,
        message_repository=message_repo,
        prior_case_queries=prior_queries,
        matrix_poster=matrix_poster,
    )

    await service.post_widget(case_id=current_case.case_id)

    assert len(matrix_poster.calls) == 2

    room_id, widget_body = matrix_poster.calls[0]
    payload = _extract_payload_from_widget_body(widget_body)

    assert room_id == "!room2:example.org"
    assert payload["case_id"] == str(current_case.case_id)
    assert payload["agency_record_number"] == "12345"
    assert payload["structured_data"]["schema_version"] == "1.1"
    assert payload["summary"] == "Resumo LLM1"
    assert payload["suggested_action"]["suggestion"] == "deny"
    assert payload["prior_case"]["prior_case_id"] == str(prior_case.case_id)
    assert payload["prior_denial_count_7d"] == 1

    ack_room_id, ack_body = matrix_poster.calls[1]
    assert ack_room_id == "!room2:example.org"
    assert str(current_case.case_id) in ack_body

    with engine.begin() as connection:
        status = connection.execute(
            sa.text("SELECT status FROM cases WHERE case_id = :case_id"),
            {"case_id": current_case.case_id.hex},
        ).scalar_one()
        kinds = connection.execute(
            sa.text(
                "SELECT kind FROM case_messages "
                "WHERE case_id = :case_id ORDER BY id"
            ),
            {"case_id": current_case.case_id.hex},
        ).scalars().all()

    assert status == "WAIT_DOCTOR"
    assert list(kinds) == ["bot_widget", "bot_ack"]
