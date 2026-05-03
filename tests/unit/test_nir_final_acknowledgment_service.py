"""Unit tests for NirFinalAcknowledgmentService.

TDD tests for slice 5.1 — validates that:
- Final result appears for NIR (case is loadable for acknowledgment).
- Valid confirmation is persisted (audit event created, cleanup job enqueued).
- Repeat confirmation is idempotent (no duplicate cleanup side effects).
- Closure effects do not duplicate.
- Wrong state cases are rejected.
- Nonexistent cases are rejected.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from triage_automation.application.ports.audit_repository_port import (
    AuditEventCreateInput,
)
from triage_automation.application.ports.job_queue_port import (
    JobEnqueueInput,
)
from triage_automation.application.services.nir_final_acknowledgment_service import (
    NirAcknowledgmentCase,
    NirFinalAcknowledgmentOutcome,
    NirFinalAcknowledgmentService,
)
from triage_automation.domain.case_status import CaseStatus

# ── Fake repositories ──────────────────────────────────────────────────

@dataclass
class FakeSnapshot:
    """Minimal fake snapshot for acknowledgment form context."""

    case_id: UUID
    status: CaseStatus
    structured_data_json: dict[str, Any] | None = None
    agency_record_number: str | None = None


@dataclass
class FakeCaseRepository:
    """Fake case repository for unit testing NirFinalAcknowledgmentService."""

    snapshots: dict[UUID, FakeSnapshot] = field(default_factory=dict)
    claim_results: dict[UUID, bool] = field(default_factory=dict)
    claim_calls: list[tuple[UUID, str]] = field(default_factory=list)

    async def get_case_doctor_decision_snapshot(
        self, *, case_id: UUID
    ) -> FakeSnapshot | None:
        """Return a snapshot for acknowledgment form rendering."""
        return self.snapshots.get(case_id)

    async def claim_cleanup_trigger_if_first(
        self, *, case_id: UUID, reactor_user_id: str
    ) -> bool:
        """Record the claim call and return configured result."""
        self.claim_calls.append((case_id, reactor_user_id))
        return self.claim_results.get(case_id, True)

    # Fallback for other port methods (unused in this service but required)
    async def create_case(self, payload: Any) -> Any:
        raise NotImplementedError

    async def create_web_case(self, payload: Any) -> Any:
        raise NotImplementedError

    async def get_case_by_origin_event_id(self, origin_event_id: str) -> Any:
        raise NotImplementedError

    async def get_case_room2_widget_snapshot(self, *, case_id: UUID) -> Any:
        raise NotImplementedError

    async def apply_doctor_decision_if_waiting(self, payload: Any) -> bool:
        raise NotImplementedError

    async def apply_scheduler_decision_if_waiting(self, payload: Any) -> bool:
        raise NotImplementedError

    async def get_case_final_reply_snapshot(self, *, case_id: UUID) -> Any:
        raise NotImplementedError

    async def mark_room1_final_reply_posted(
        self, *, case_id: UUID, room1_final_reply_event_id: str
    ) -> bool:
        raise NotImplementedError

    async def get_by_room1_final_reply_event_id(
        self, *, room1_final_reply_event_id: str
    ) -> Any:
        raise NotImplementedError

    async def mark_cleanup_completed(self, *, case_id: UUID) -> None:
        raise NotImplementedError

    async def list_non_terminal_cases_for_recovery(self) -> Any:
        raise NotImplementedError

    async def list_cases_for_monitoring(self, *, filters: Any) -> Any:
        raise NotImplementedError

    async def get_case_monitoring_detail(self, *, case_id: UUID) -> Any:
        raise NotImplementedError

    async def update_status(self, *, case_id: UUID, status: CaseStatus) -> None:
        raise NotImplementedError

    async def store_pdf_extraction(
        self, *, case_id: UUID, pdf_mxc_url: str,
        extracted_text: str, agency_record_number: str | None = None,
        agency_record_extracted_at: datetime | None = None,
    ) -> None:
        raise NotImplementedError

    async def append_case_report_transcript(
        self, *, case_id: UUID, extracted_text: str,
    ) -> None:
        raise NotImplementedError

    async def append_case_llm_interaction(self, payload: Any) -> None:
        raise NotImplementedError

    async def store_llm1_artifacts(
        self, *, case_id: UUID, structured_data_json: dict[str, Any],
        summary_text: str,
    ) -> None:
        raise NotImplementedError

    async def store_llm2_artifacts(
        self, *, case_id: UUID, suggested_action_json: dict[str, Any],
    ) -> None:
        raise NotImplementedError


@dataclass
class FakeAuditRepository:
    """Fake audit repository for unit testing NirFinalAcknowledgmentService."""

    events: list[AuditEventCreateInput] = field(default_factory=list)

    async def append_event(self, payload: AuditEventCreateInput) -> int:
        """Record event and return fake id."""
        self.events.append(payload)
        return len(self.events)


@dataclass
class FakeJobQueue:
    """Fake job queue for unit testing NirFinalAcknowledgmentService."""

    jobs: list[JobEnqueueInput] = field(default_factory=list)

    async def enqueue(self, payload: JobEnqueueInput) -> None:
        """Record enqueued job."""
        self.jobs.append(payload)


# ── Fixtures ──────────────────────────────────────────────────────────

def _make_service() -> tuple[
    NirFinalAcknowledgmentService, FakeCaseRepository, FakeAuditRepository, FakeJobQueue
]:
    """Create a fresh service with fake dependencies."""
    case_repo = FakeCaseRepository()
    audit_repo = FakeAuditRepository()
    job_queue = FakeJobQueue()
    service = NirFinalAcknowledgmentService(
        case_repository=case_repo,  # type: ignore[arg-type]
        audit_repository=audit_repo,
        job_queue=job_queue,  # type: ignore[arg-type]
    )
    return service, case_repo, audit_repo, job_queue


def _setup_case_in_state(
    case_repo: FakeCaseRepository,
    *,
    case_id: UUID,
    status: CaseStatus,
    claim_result: bool = True,
) -> None:
    """Helper: register a case snapshot with given status in the fake repo."""
    case_repo.snapshots[case_id] = FakeSnapshot(
        case_id=case_id,
        status=status,
    )
    case_repo.claim_results[case_id] = claim_result


# ── Tests: get_acknowledgment_case ────────────────────────────────────


class TestGetAcknowledgmentCase:
    """NIR can load case data for the acknowledgment view."""

    def test_returns_case_when_awaiting_cleanup_thumbs(self) -> None:
        """Case in WAIT_R1_CLEANUP_THUMBS is loadable for acknowledgment."""
        service, case_repo, _, _ = _make_service()
        case_id = uuid4()
        _setup_case_in_state(case_repo, case_id=case_id, status=CaseStatus.WAIT_R1_CLEANUP_THUMBS)

        result = service.get_acknowledgment_case(case_id=case_id)

        assert result is not None
        assert isinstance(result, NirAcknowledgmentCase)
        assert result.case_id == case_id
        assert result.status == CaseStatus.WAIT_R1_CLEANUP_THUMBS

    def test_returns_none_for_nonexistent_case(self) -> None:
        """Nonexistent case returns None."""
        service, _, _, _ = _make_service()
        result = service.get_acknowledgment_case(case_id=uuid4())
        assert result is None

    def test_returns_none_for_wrong_state(self) -> None:
        """Cases not in WAIT_R1_CLEANUP_THUMBS return None."""
        service, case_repo, _, _ = _make_service()
        case_id = uuid4()
        _setup_case_in_state(case_repo, case_id=case_id, status=CaseStatus.WAIT_DOCTOR)

        result = service.get_acknowledgment_case(case_id=case_id)
        assert result is None

    def test_returns_none_for_already_cleaned(self) -> None:
        """Already CLEANED cases return None."""
        service, case_repo, _, _ = _make_service()
        case_id = uuid4()
        _setup_case_in_state(case_repo, case_id=case_id, status=CaseStatus.CLEANED)

        result = service.get_acknowledgment_case(case_id=case_id)
        assert result is None

    def test_returns_none_for_cleanup_running(self) -> None:
        """Cases already in CLEANUP_RUNNING return None."""
        service, case_repo, _, _ = _make_service()
        case_id = uuid4()
        _setup_case_in_state(case_repo, case_id=case_id, status=CaseStatus.CLEANUP_RUNNING)

        result = service.get_acknowledgment_case(case_id=case_id)
        assert result is None


# ── Tests: acknowledge (async) ────────────────────────────────────────


class TestAcknowledgeSuccess:
    """Valid acknowledgment is persisted and triggers cleanup."""

    @pytest.mark.asyncio
    async def test_valid_acknowledgment_returns_applied(self) -> None:
        """Valid acknowledgment returns APPLIED outcome."""
        service, case_repo, _, _ = _make_service()
        case_id = uuid4()
        _setup_case_in_state(case_repo, case_id=case_id, status=CaseStatus.WAIT_R1_CLEANUP_THUMBS)

        result = await service.acknowledge(
            case_id=case_id,
            nir_user_id="nir-1",
            actor_email="nir@example.com",
        )

        assert result.outcome == NirFinalAcknowledgmentOutcome.APPLIED

    @pytest.mark.asyncio
    async def test_valid_acknowledgment_creates_audit_event(self) -> None:
        """Valid acknowledgment persists a NIR_FINAL_ACKNOWLEDGMENT audit event."""
        service, case_repo, audit_repo, _ = _make_service()
        case_id = uuid4()
        _setup_case_in_state(case_repo, case_id=case_id, status=CaseStatus.WAIT_R1_CLEANUP_THUMBS)

        await service.acknowledge(
            case_id=case_id,
            nir_user_id="nir-1",
            actor_email="nir@example.com",
        )

        assert len(audit_repo.events) >= 2  # At least web human event + system trigger audit

        # Find the web human acknowledgment event
        web_events = [
            e for e in audit_repo.events
            if e.event_type == "NIR_FINAL_ACKNOWLEDGMENT"
        ]
        assert len(web_events) == 1
        web_event = web_events[0]
        assert web_event.case_id == case_id
        assert web_event.actor_type == "web_human"
        assert web_event.actor_user_id == "nir-1"
        assert web_event.payload["origin"] == "web"
        assert web_event.payload["actor"] == "nir@example.com"

    @pytest.mark.asyncio
    async def test_valid_acknowledgment_enqueues_cleanup_job(self) -> None:
        """Valid acknowledgment enqueues execute_cleanup job."""
        service, case_repo, _, job_queue = _make_service()
        case_id = uuid4()
        _setup_case_in_state(case_repo, case_id=case_id, status=CaseStatus.WAIT_R1_CLEANUP_THUMBS)

        await service.acknowledge(
            case_id=case_id,
            nir_user_id="nir-1",
            actor_email="nir@example.com",
        )

        assert len(job_queue.jobs) == 1
        assert job_queue.jobs[0].case_id == case_id
        assert job_queue.jobs[0].job_type == "execute_cleanup"

    @pytest.mark.asyncio
    async def test_valid_acknowledgment_calls_claim_cleanup_trigger_once(self) -> None:
        """Valid acknowledgment calls claim_cleanup_trigger_if_first exactly once."""
        service, case_repo, _, _ = _make_service()
        case_id = uuid4()
        _setup_case_in_state(case_repo, case_id=case_id, status=CaseStatus.WAIT_R1_CLEANUP_THUMBS)

        await service.acknowledge(
            case_id=case_id,
            nir_user_id="nir-1",
            actor_email="nir@example.com",
        )

        assert len(case_repo.claim_calls) == 1
        assert case_repo.claim_calls[0] == (case_id, "nir-1")

    @pytest.mark.asyncio
    async def test_acknowledgment_persists_system_trigger_audit_event(self) -> None:
        """Acknowledgment creates system-level trigger audit event."""
        service, case_repo, audit_repo, _ = _make_service()
        case_id = uuid4()
        _setup_case_in_state(case_repo, case_id=case_id, status=CaseStatus.WAIT_R1_CLEANUP_THUMBS)

        await service.acknowledge(
            case_id=case_id,
            nir_user_id="nir-1",
            actor_email="nir@example.com",
        )

        system_events = [
            e for e in audit_repo.events
            if e.event_type == "NIR_FINAL_ACK_TRIGGERED_CLEANUP"
        ]
        assert len(system_events) == 1
        assert system_events[0].case_id == case_id
        assert system_events[0].actor_type == "system"


class TestAcknowledgeIdempotency:
    """Repeat acknowledgment is idempotent and does not duplicate effects."""

    @pytest.mark.asyncio
    async def test_repeat_acknowledgment_returns_duplicate_outcome(self) -> None:
        """Repeat acknowledgment returns DUPLICATE_OR_RACE outcome."""
        service, case_repo, _, _ = _make_service()
        case_id = uuid4()
        _setup_case_in_state(
            case_repo, case_id=case_id,
            status=CaseStatus.WAIT_R1_CLEANUP_THUMBS, claim_result=True,
        )

        # First ack — succeeds
        result1 = await service.acknowledge(
            case_id=case_id,
            nir_user_id="nir-1",
            actor_email="nir@example.com",
        )
        assert result1.outcome == NirFinalAcknowledgmentOutcome.APPLIED

        # Configure subsequent claim to fail
        case_repo.claim_results[case_id] = False

        # Second ack — idempotent rejection
        result2 = await service.acknowledge(
            case_id=case_id,
            nir_user_id="nir-2",
            actor_email="nir2@example.com",
        )
        assert result2.outcome == NirFinalAcknowledgmentOutcome.DUPLICATE_OR_RACE

    @pytest.mark.asyncio
    async def test_repeat_acknowledgment_does_not_duplicate_cleanup_job(self) -> None:
        """Repeat acknowledgment does not enqueue cleanup job again."""
        service, case_repo, _, job_queue = _make_service()
        case_id = uuid4()
        _setup_case_in_state(
            case_repo, case_id=case_id,
            status=CaseStatus.WAIT_R1_CLEANUP_THUMBS, claim_result=True,
        )

        # First ack
        await service.acknowledge(
            case_id=case_id, nir_user_id="nir-1", actor_email="nir@example.com"
        )
        assert len(job_queue.jobs) == 1

        # Configure subsequent claim to fail
        case_repo.claim_results[case_id] = False

        # Second ack
        await service.acknowledge(
            case_id=case_id, nir_user_id="nir-2", actor_email="nir2@example.com"
        )

        # No additional job enqueued
        assert len(job_queue.jobs) == 1

    @pytest.mark.asyncio
    async def test_repeat_acknowledgment_does_not_duplicate_audit_events(self) -> None:
        """Repeat acknowledgment does not duplicate web human audit events."""
        service, case_repo, audit_repo, _ = _make_service()
        case_id = uuid4()
        _setup_case_in_state(
            case_repo, case_id=case_id,
            status=CaseStatus.WAIT_R1_CLEANUP_THUMBS, claim_result=True,
        )

        await service.acknowledge(
            case_id=case_id, nir_user_id="nir-1", actor_email="nir@example.com"
        )

        case_repo.claim_results[case_id] = False

        await service.acknowledge(
            case_id=case_id, nir_user_id="nir-2", actor_email="nir2@example.com"
        )

        web_events = [
            e for e in audit_repo.events
            if e.event_type == "NIR_FINAL_ACKNOWLEDGMENT"
        ]
        assert len(web_events) == 1


class TestAcknowledgeErrors:
    """Error states are handled deterministically."""

    @pytest.mark.asyncio
    async def test_nonexistent_case_returns_not_found(self) -> None:
        """Nonexistent case returns NOT_FOUND outcome."""
        service, _, _, _ = _make_service()
        result = await service.acknowledge(
            case_id=uuid4(),
            nir_user_id="nir-1",
            actor_email="nir@example.com",
        )
        assert result.outcome == NirFinalAcknowledgmentOutcome.NOT_FOUND

    @pytest.mark.asyncio
    async def test_wrong_state_case_returns_wrong_state(self) -> None:
        """Cases not in WAIT_R1_CLEANUP_THUMBS return WRONG_STATE."""
        service, case_repo, _, _ = _make_service()
        case_id = uuid4()
        _setup_case_in_state(case_repo, case_id=case_id, status=CaseStatus.WAIT_DOCTOR)

        result = await service.acknowledge(
            case_id=case_id,
            nir_user_id="nir-1",
            actor_email="nir@example.com",
        )
        assert result.outcome == NirFinalAcknowledgmentOutcome.WRONG_STATE

    @pytest.mark.asyncio
    async def test_cleaned_case_returns_wrong_state(self) -> None:
        """Already CLEANED cases return WRONG_STATE."""
        service, case_repo, _, _ = _make_service()
        case_id = uuid4()
        _setup_case_in_state(case_repo, case_id=case_id, status=CaseStatus.CLEANED)

        result = await service.acknowledge(
            case_id=case_id,
            nir_user_id="nir-1",
            actor_email="nir@example.com",
        )
        assert result.outcome == NirFinalAcknowledgmentOutcome.WRONG_STATE

    @pytest.mark.asyncio
    async def test_cleanup_running_case_returns_wrong_state(self) -> None:
        """Cases in CLEANUP_RUNNING return WRONG_STATE."""
        service, case_repo, _, _ = _make_service()
        case_id = uuid4()
        _setup_case_in_state(case_repo, case_id=case_id, status=CaseStatus.CLEANUP_RUNNING)

        result = await service.acknowledge(
            case_id=case_id,
            nir_user_id="nir-1",
            actor_email="nir@example.com",
        )
        assert result.outcome == NirFinalAcknowledgmentOutcome.WRONG_STATE

    @pytest.mark.asyncio
    async def test_wrong_state_does_not_enqueue_job(self) -> None:
        """Wrong state acknowledgment does not enqueue any jobs."""
        service, case_repo, _, job_queue = _make_service()
        case_id = uuid4()
        _setup_case_in_state(case_repo, case_id=case_id, status=CaseStatus.WAIT_DOCTOR)

        await service.acknowledge(
            case_id=case_id, nir_user_id="nir-1", actor_email="nir@example.com"
        )

        assert len(job_queue.jobs) == 0

    @pytest.mark.asyncio
    async def test_not_found_does_not_enqueue_job(self) -> None:
        """Not found case does not enqueue any jobs."""
        service, _, _, job_queue = _make_service()
        await service.acknowledge(
            case_id=uuid4(), nir_user_id="nir-1", actor_email="nir@example.com"
        )

        assert len(job_queue.jobs) == 0
