"""Port for case persistence operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from triage_automation.domain.case_status import CaseStatus


class DuplicateCaseOriginEventError(ValueError):
    """Raised when a case with the same room1 origin event already exists."""


@dataclass(frozen=True)
class CaseCreateInput:
    """Input payload for creating a case row."""

    case_id: UUID
    status: CaseStatus
    room1_origin_room_id: str
    room1_origin_event_id: str
    room1_sender_user_id: str


@dataclass(frozen=True)
class CaseRecord:
    """Case persistence model used across repository boundaries."""

    case_id: UUID
    status: CaseStatus
    room1_origin_room_id: str
    room1_origin_event_id: str
    room1_sender_user_id: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class CaseRoom2WidgetSnapshot:
    """Case fields required to build and post the Room-2 widget payload."""

    case_id: UUID
    status: CaseStatus
    agency_record_number: str | None
    structured_data_json: dict[str, Any] | None
    summary_text: str | None
    suggested_action_json: dict[str, Any] | None


class CaseRepositoryPort(Protocol):
    """Async case repository contract."""

    async def create_case(self, payload: CaseCreateInput) -> CaseRecord:
        """Create a case row or raise DuplicateCaseOriginEventError."""

    async def get_case_by_origin_event_id(self, origin_event_id: str) -> CaseRecord | None:
        """Retrieve case by Room-1 origin event id."""

    async def get_case_room2_widget_snapshot(
        self,
        *,
        case_id: UUID,
    ) -> CaseRoom2WidgetSnapshot | None:
        """Load case artifacts used by Room-2 widget posting flow."""

    async def update_status(self, *, case_id: UUID, status: CaseStatus) -> None:
        """Update case status and touch updated_at timestamp."""

    async def store_pdf_extraction(
        self,
        *,
        case_id: UUID,
        pdf_mxc_url: str,
        extracted_text: str,
        agency_record_number: str | None = None,
        agency_record_extracted_at: datetime | None = None,
    ) -> None:
        """Persist PDF source, extracted/cleaned text, and optional record extraction fields."""

    async def store_llm1_artifacts(
        self,
        *,
        case_id: UUID,
        structured_data_json: dict[str, Any],
        summary_text: str,
    ) -> None:
        """Persist validated LLM1 structured payload and summary text."""

    async def store_llm2_artifacts(
        self,
        *,
        case_id: UUID,
        suggested_action_json: dict[str, Any],
    ) -> None:
        """Persist validated and policy-reconciled LLM2 suggestion payload."""
