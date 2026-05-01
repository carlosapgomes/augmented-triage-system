"""Tests for web workflow queue projections and web event timeline contract.

Validates that:
- doctor queue includes only cases awaiting medical decision;
- scheduler queue includes only cases awaiting scheduling;
- nir queue includes recent/active cases for the NIR operator;
- queue items expose deterministic minimal card fields;
- web event timeline contract is explicit and reusable.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from triage_automation.domain.case_status import CaseStatus
from triage_automation.domain.web_event_contract import (
    WebEventOrigin,
    WebEventType,
    WebHumanEvent,
)
from triage_automation.domain.web_workflow_projections import (
    CaseCardFields,
    DoctorQueueProjection,
    NIRQueueProjection,
    SchedulerQueueProjection,
    derive_doctor_queue,
    derive_nir_queue,
    derive_scheduler_queue,
)


def _make_card(
    *,
    case_id: UUID | None = None,
    status: CaseStatus = CaseStatus.WAIT_DOCTOR,
    latest_activity_at: datetime | None = None,
    agency_record_number: str | None = None,
    patient_name: str | None = None,
    compact_summary: str = "EM_ANDAMENTO",
) -> CaseCardFields:
    """Create a CaseCardFields with sensible defaults for testing."""
    return CaseCardFields(
        case_id=case_id or uuid4(),
        status=status,
        latest_activity_at=latest_activity_at or datetime.now(tz=UTC),
        agency_record_number=agency_record_number,
        patient_name=patient_name,
        compact_summary=compact_summary,
    )


# ── Doctor queue projections ──────────────────────────────────────────


class TestDoctorQueueProjection:
    """Doctor queue: only cases in WAIT_DOCTOR status."""

    def test_wait_doctor_appears_in_doctor_queue(self) -> None:
        items = [_make_card(status=CaseStatus.WAIT_DOCTOR)]
        result = derive_doctor_queue(items)
        assert len(result.items) == 1

    def test_non_wait_doctor_excluded_from_doctor_queue(self) -> None:
        items = [
            _make_card(status=CaseStatus.NEW),
            _make_card(status=CaseStatus.WAIT_APPT),
            _make_card(status=CaseStatus.CLEANED),
        ]
        result = derive_doctor_queue(items)
        assert len(result.items) == 0

    def test_doctor_queue_preserves_card_fields(self) -> None:
        cid = uuid4()
        ts = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
        items = [
            _make_card(
                case_id=cid,
                status=CaseStatus.WAIT_DOCTOR,
                latest_activity_at=ts,
                agency_record_number="REG-001",
                patient_name="Maria Silva",
                compact_summary="EM_ANDAMENTO · AGUARDANDO_SALA_2",
            )
        ]
        result = derive_doctor_queue(items)
        assert len(result.items) == 1
        card = result.items[0]
        assert card.case_id == cid
        assert card.status == CaseStatus.WAIT_DOCTOR
        assert card.latest_activity_at == ts
        assert card.agency_record_number == "REG-001"
        assert card.patient_name == "Maria Silva"
        assert card.compact_summary == "EM_ANDAMENTO · AGUARDANDO_SALA_2"

    def test_doctor_queue_orders_by_latest_activity_desc(self) -> None:
        older = _make_card(
            status=CaseStatus.WAIT_DOCTOR,
            latest_activity_at=datetime(2026, 5, 1, 10, 0, tzinfo=UTC),
        )
        newer = _make_card(
            status=CaseStatus.WAIT_DOCTOR,
            latest_activity_at=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        )
        result = derive_doctor_queue([older, newer])
        assert result.items[0].latest_activity_at > result.items[1].latest_activity_at


# ── Scheduler queue projections ────────────────────────────────────────


class TestSchedulerQueueProjection:
    """Scheduler queue: only cases in WAIT_APPT status."""

    def test_wait_appt_appears_in_scheduler_queue(self) -> None:
        items = [_make_card(status=CaseStatus.WAIT_APPT)]
        result = derive_scheduler_queue(items)
        assert len(result.items) == 1

    def test_non_wait_appt_excluded_from_scheduler_queue(self) -> None:
        items = [
            _make_card(status=CaseStatus.WAIT_DOCTOR),
            _make_card(status=CaseStatus.APPT_CONFIRMED),
            _make_card(status=CaseStatus.CLEANED),
        ]
        result = derive_scheduler_queue(items)
        assert len(result.items) == 0

    def test_scheduler_queue_preserves_card_fields(self) -> None:
        cid = uuid4()
        ts = datetime(2026, 5, 1, 14, 0, tzinfo=UTC)
        items = [
            _make_card(
                case_id=cid,
                status=CaseStatus.WAIT_APPT,
                latest_activity_at=ts,
                agency_record_number="REG-002",
                patient_name="João Souza",
            )
        ]
        result = derive_scheduler_queue(items)
        assert len(result.items) == 1
        card = result.items[0]
        assert card.case_id == cid
        assert card.status == CaseStatus.WAIT_APPT
        assert card.latest_activity_at == ts
        assert card.agency_record_number == "REG-002"
        assert card.patient_name == "João Souza"

    def test_scheduler_queue_orders_by_latest_activity_desc(self) -> None:
        older = _make_card(
            status=CaseStatus.WAIT_APPT,
            latest_activity_at=datetime(2026, 5, 1, 9, 0, tzinfo=UTC),
        )
        newer = _make_card(
            status=CaseStatus.WAIT_APPT,
            latest_activity_at=datetime(2026, 5, 1, 11, 0, tzinfo=UTC),
        )
        result = derive_scheduler_queue([older, newer])
        assert result.items[0].latest_activity_at > result.items[1].latest_activity_at


# ── NIR queue projections ──────────────────────────────────────────────


class TestNIRQueueProjection:
    """NIR queue: recent/active cases excluding fully cleaned ones."""

    def test_active_cases_appear_in_nir_queue(self) -> None:
        items = [
            _make_card(status=CaseStatus.WAIT_DOCTOR),
            _make_card(status=CaseStatus.WAIT_APPT),
        ]
        result = derive_nir_queue(items)
        assert len(result.items) == 2

    def test_cleaned_cases_excluded_from_nir_queue(self) -> None:
        items = [_make_card(status=CaseStatus.CLEANED)]
        result = derive_nir_queue(items)
        assert len(result.items) == 0

    def test_nir_queue_includes_final_reply_and_cleanup_waiting(self) -> None:
        items = [
            _make_card(status=CaseStatus.WAIT_R1_CLEANUP_THUMBS),
            _make_card(status=CaseStatus.CLEANUP_RUNNING),
        ]
        result = derive_nir_queue(items)
        assert len(result.items) == 2

    def test_nir_queue_preserves_card_fields(self) -> None:
        cid = uuid4()
        ts = datetime(2026, 5, 1, 15, 0, tzinfo=UTC)
        items = [
            _make_card(
                case_id=cid,
                status=CaseStatus.WAIT_DOCTOR,
                latest_activity_at=ts,
                agency_record_number="REG-003",
                patient_name="Ana Costa",
                compact_summary="EM_ANDAMENTO · AGUARDANDO_SALA_2",
            )
        ]
        result = derive_nir_queue(items)
        card = result.items[0]
        assert card.case_id == cid
        assert card.compact_summary == "EM_ANDAMENTO · AGUARDANDO_SALA_2"

    def test_nir_queue_orders_by_latest_activity_desc(self) -> None:
        older = _make_card(
            status=CaseStatus.WAIT_DOCTOR,
            latest_activity_at=datetime(2026, 5, 1, 8, 0, tzinfo=UTC),
        )
        newer = _make_card(
            status=CaseStatus.WAIT_APPT,
            latest_activity_at=datetime(2026, 5, 1, 10, 0, tzinfo=UTC),
        )
        result = derive_nir_queue([older, newer])
        assert result.items[0].latest_activity_at > result.items[1].latest_activity_at


# ── Web event timeline contract ────────────────────────────────────────


class TestWebHumanEventContract:
    """Contract: each web event carries origin, actor, timestamp, payload, case_id."""

    def test_web_event_carries_required_fields(self) -> None:
        cid = uuid4()
        ts = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
        event = WebHumanEvent(
            case_id=cid,
            origin=WebEventOrigin.WEB,
            actor="nir@example.com",
            timestamp=ts,
            event_type=WebEventType.NIR_PDF_UPLOAD,
            summary_text="PDF uploaded for case",
        )
        assert event.case_id == cid
        assert event.origin == WebEventOrigin.WEB
        assert event.actor == "nir@example.com"
        assert event.timestamp == ts
        assert event.event_type == WebEventType.NIR_PDF_UPLOAD
        assert event.summary_text == "PDF uploaded for case"

    def test_web_event_origins_are_distinct(self) -> None:
        origins = {
            WebEventOrigin.WEB,
            WebEventOrigin.PDF,
            WebEventOrigin.LLM,
            WebEventOrigin.SYSTEM,
        }
        assert len(origins) == 4
        assert WebEventOrigin.WEB not in {WebEventOrigin.PDF, WebEventOrigin.LLM}

    def test_web_event_types_cover_all_human_web_actions(self) -> None:
        expected_types = {
            "NIR_PDF_UPLOAD",
            "DOCTOR_DECISION",
            "SCHEDULER_CONFIRMATION",
            "NIR_FINAL_ACKNOWLEDGMENT",
        }
        actual_types = {t.value for t in WebEventType}
        assert expected_types.issubset(actual_types)

    def test_web_event_is_frozen(self) -> None:
        event = WebHumanEvent(
            case_id=uuid4(),
            origin=WebEventOrigin.WEB,
            actor="doctor@example.com",
            timestamp=datetime.now(tz=UTC),
            event_type=WebEventType.DOCTOR_DECISION,
            summary_text="Decision: accept",
        )
        with pytest.raises(AttributeError):
            event.actor = "other@example.com"  # type: ignore[misc]

    def test_case_queue_projections_return_typed_results(self) -> None:
        items = [_make_card(status=CaseStatus.WAIT_DOCTOR)]
        dr = derive_doctor_queue(items)
        assert isinstance(dr, DoctorQueueProjection)
        assert isinstance(dr.items, list)

        sr = derive_scheduler_queue(items)
        assert isinstance(sr, SchedulerQueueProjection)
        assert isinstance(sr.items, list)

        nr = derive_nir_queue(items)
        assert isinstance(nr, NIRQueueProjection)
        assert isinstance(nr.items, list)
