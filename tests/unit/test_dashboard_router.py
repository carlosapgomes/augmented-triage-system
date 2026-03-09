from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from triage_automation.application.ports.case_repository_port import CaseMonitoringTimelineItem
from triage_automation.infrastructure.http.dashboard_router import (
    _extract_pdf_report_text_from_timeline,
)


def _timeline_item(
    *,
    event_type: str,
    content_text: str | None,
    source: Literal["pdf", "llm", "matrix"] = "matrix",
) -> CaseMonitoringTimelineItem:
    return CaseMonitoringTimelineItem(
        source=source,
        channel="pdf" if source == "pdf" else "!room1:example.org",
        timestamp=datetime(2026, 2, 18, 10, 0, 0, tzinfo=UTC),
        room_id=None if source == "pdf" else "!room1:example.org",
        actor="system",
        event_type=event_type,
        content_text=content_text,
        payload=None,
    )


def test_extract_pdf_report_text_from_timeline_returns_latest_pdf_text() -> None:
    timeline = [
        _timeline_item(
            source="pdf",
            event_type="pdf_report_extracted",
            content_text="Primeira versao",
        ),
        _timeline_item(event_type="bot_processing", content_text="processando..."),
        _timeline_item(
            source="pdf",
            event_type="pdf_report_extracted",
            content_text="Versao mais recente",
        ),
    ]

    extracted = _extract_pdf_report_text_from_timeline(timeline)

    assert extracted == "Versao mais recente"


def test_extract_pdf_report_text_from_timeline_returns_none_when_absent() -> None:
    timeline = [
        _timeline_item(event_type="bot_processing", content_text="processando..."),
        _timeline_item(event_type="room2_doctor_reply", content_text="decisao: aceitar"),
    ]

    extracted = _extract_pdf_report_text_from_timeline(timeline)

    assert extracted is None
