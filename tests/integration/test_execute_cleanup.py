from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.config import Config

from alembic import command
from triage_automation.application.ports.case_repository_port import CaseCreateInput
from triage_automation.application.ports.message_repository_port import CaseMessageCreateInput
from triage_automation.application.services.execute_cleanup_service import ExecuteCleanupService
from triage_automation.domain.case_status import CaseStatus
from triage_automation.infrastructure.db.audit_repository import SqlAlchemyAuditRepository
from triage_automation.infrastructure.db.case_repository import SqlAlchemyCaseRepository
from triage_automation.infrastructure.db.message_repository import SqlAlchemyMessageRepository
from triage_automation.infrastructure.db.session import create_session_factory


class FakeMatrixRedactor:
    def __init__(self, *, fail_event_ids: set[str] | None = None) -> None:
        self._fail_event_ids = fail_event_ids or set()
        self.calls: list[tuple[str, str]] = []

    async def redact_event(self, *, room_id: str, event_id: str) -> None:
        self.calls.append((room_id, event_id))
        if event_id in self._fail_event_ids:
            raise RuntimeError(f"failed to redact {event_id}")


def _upgrade_head(tmp_path: Path, filename: str) -> tuple[str, str]:
    db_path = tmp_path / filename
    sync_url = f"sqlite+pysqlite:///{db_path}"
    async_url = f"sqlite+aiosqlite:///{db_path}"

    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(alembic_config, "head")

    return sync_url, async_url


def _decode_json(value: object) -> dict[str, object]:
    if isinstance(value, str):
        parsed = json.loads(value)
        assert isinstance(parsed, dict)
        return parsed
    assert isinstance(value, dict)
    return value


@pytest.mark.asyncio
async def test_cleanup_redacts_messages_audits_results_and_marks_case_cleaned(
    tmp_path: Path,
) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "cleanup_execute.db")
    session_factory = create_session_factory(async_url)

    case_repo = SqlAlchemyCaseRepository(session_factory)
    audit_repo = SqlAlchemyAuditRepository(session_factory)
    message_repo = SqlAlchemyMessageRepository(session_factory)

    created_case = await case_repo.create_case(
        CaseCreateInput(
            case_id=uuid4(),
            status=CaseStatus.CLEANUP_RUNNING,
            room1_origin_room_id="!room1:example.org",
            room1_origin_event_id="$origin-cleanup-1",
            room1_sender_user_id="@human:example.org",
        )
    )

    await message_repo.add_message(
        CaseMessageCreateInput(
            case_id=created_case.case_id,
            room_id="!room1:example.org",
            event_id="$origin-cleanup-1",
            kind="room1_origin",
            sender_user_id="@human:example.org",
        )
    )
    await message_repo.add_message(
        CaseMessageCreateInput(
            case_id=created_case.case_id,
            room_id="!room2:example.org",
            event_id="$room2-widget-1",
            kind="bot_widget",
            sender_user_id=None,
        )
    )
    await message_repo.add_message(
        CaseMessageCreateInput(
            case_id=created_case.case_id,
            room_id="!room3:example.org",
            event_id="$room3-request-1",
            kind="room3_request",
            sender_user_id=None,
        )
    )

    redactor = FakeMatrixRedactor(fail_event_ids={"$room2-widget-1"})
    service = ExecuteCleanupService(
        case_repository=case_repo,
        audit_repository=audit_repo,
        message_repository=message_repo,
        matrix_redactor=redactor,
    )

    result = await service.execute(case_id=created_case.case_id)

    assert result.redacted_success == 2
    assert result.redacted_failed == 1
    assert set(redactor.calls) == {
        ("!room1:example.org", "$origin-cleanup-1"),
        ("!room2:example.org", "$room2-widget-1"),
        ("!room3:example.org", "$room3-request-1"),
    }

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        case_row = connection.execute(
            sa.text(
                "SELECT status, cleanup_completed_at "
                "FROM cases WHERE case_id = :case_id"
            ),
            {"case_id": created_case.case_id.hex},
        ).mappings().one()
        event_rows = connection.execute(
            sa.text(
                "SELECT event_type, payload FROM case_events "
                "WHERE case_id = :case_id ORDER BY id"
            ),
            {"case_id": created_case.case_id.hex},
        ).mappings().all()

    assert case_row["status"] == "CLEANED"
    assert case_row["cleanup_completed_at"] is not None

    event_types = [str(row["event_type"]) for row in event_rows]
    assert event_types.count("MATRIX_EVENT_REDACTED") == 2
    assert event_types.count("MATRIX_EVENT_REDACTION_FAILED") == 1
    assert event_types.count("CLEANUP_COMPLETED") == 1

    cleanup_event = next(row for row in event_rows if row["event_type"] == "CLEANUP_COMPLETED")
    payload = _decode_json(cleanup_event["payload"])
    assert payload["count_redacted_success"] == 2
    assert payload["count_redacted_failed"] == 1
