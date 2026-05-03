from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from triage_automation.application.ports.case_repository_port import CaseMonitoringTimelineItem
from triage_automation.infrastructure.http.dashboard_router import (
    _build_thread_node,
    _event_badge_class,
    _extract_pdf_report_text_from_timeline,
    _source_badge_class,
    _translate_event_type,
)


def _timeline_item(
    *,
    event_type: str,
    content_text: str | None,
    source: Literal["pdf", "llm", "matrix", "web"] = "matrix",
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


class TestWebSourceBadgeAndTranslation:
    """Dashboard router maps web source events to proper badges and labels."""

    def test_source_badge_class_for_web(self) -> None:
        """Web source gets a distinct badge class."""
        badge = _source_badge_class("web")
        assert badge is not None
        assert badge != _source_badge_class("matrix")
        assert badge != _source_badge_class("pdf")
        assert badge != _source_badge_class("llm")

    def test_translate_web_event_types(self) -> None:
        """All four web event types have user-facing Portuguese labels."""
        assert _translate_event_type("NIR_PDF_UPLOAD") != "NIR_PDF_UPLOAD"
        assert _translate_event_type("DOCTOR_DECISION") != "DOCTOR_DECISION"
        assert _translate_event_type("SCHEDULER_CONFIRMATION") != "SCHEDULER_CONFIRMATION"
        assert _translate_event_type("NIR_FINAL_ACKNOWLEDGMENT") != "NIR_FINAL_ACKNOWLEDGMENT"

    def test_event_badge_class_for_web_events(self) -> None:
        """Web event types get appropriate badge classes."""
        for et in (
            "NIR_PDF_UPLOAD",
            "DOCTOR_DECISION",
            "SCHEDULER_CONFIRMATION",
            "NIR_FINAL_ACKNOWLEDGMENT",
        ):
            badge = _event_badge_class(et)
            assert badge is not None

    def test_build_thread_node_returns_none_for_web_event_without_special_handling(self) -> None:
        """Web events that don't map to Room-1/2/3 sections return None."""
        item = _timeline_item(
            source="web",
            event_type="NIR_PDF_UPLOAD",
            content_text="PDF uploaded via web",
        )
        result = _build_thread_node(item)
        # Web events currently don't have special thread section mapping
        # (the legacy thread view is Room-1/2/3-centric)
        assert result is None
