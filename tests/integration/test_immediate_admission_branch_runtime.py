from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic.config import Config

from alembic import command
from apps.worker.main import build_worker_runtime
from triage_automation.application.ports.case_repository_port import (
    CaseCreateInput,
    DoctorDecisionUpdateInput,
)
from triage_automation.application.ports.job_queue_port import JobEnqueueInput
from triage_automation.application.ports.message_repository_port import (
    CaseMatrixMessageTranscriptCreateInput,
)
from triage_automation.application.services.reaction_service import (
    ReactionEvent,
    ReactionService,
)
from triage_automation.config.settings import Settings
from triage_automation.domain.case_status import CaseStatus
from triage_automation.infrastructure.db.audit_repository import SqlAlchemyAuditRepository
from triage_automation.infrastructure.db.case_repository import SqlAlchemyCaseRepository
from triage_automation.infrastructure.db.job_queue_repository import SqlAlchemyJobQueueRepository
from triage_automation.infrastructure.db.message_repository import SqlAlchemyMessageRepository
from triage_automation.infrastructure.db.reaction_checkpoint_repository import (
    SqlAlchemyReactionCheckpointRepository,
)
from triage_automation.infrastructure.db.session import create_session_factory


def _upgrade_head(tmp_path: Path, filename: str) -> tuple[str, str]:
    db_path = tmp_path / filename
    sync_url = f"sqlite+pysqlite:///{db_path}"
    async_url = f"sqlite+aiosqlite:///{db_path}"

    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(alembic_config, "head")

    return sync_url, async_url


def _set_required_env(monkeypatch: pytest.MonkeyPatch) -> Settings:
    del monkeypatch
    return Settings.model_construct(
        room1_id="!room1:example.org",
        room2_id="!room2:example.org",
        room3_id="!room3:example.org",
        room4_id="!room4:example.org",
        matrix_homeserver_url="https://matrix.example.org",
        matrix_bot_user_id="@bot:example.org",
        matrix_access_token="matrix-token",
        matrix_sync_timeout_ms=30_000,
        matrix_poll_interval_seconds=0.0,
        worker_poll_interval_seconds=0.0,
        worker_claim_limit=10,
        supervisor_summary_timezone="America/Bahia",
        supervisor_summary_morning_hour=7,
        supervisor_summary_evening_hour=19,
        webhook_public_url="https://webhook.example.org",
        widget_public_url="https://webhook.example.org",
        database_url="sqlite+aiosqlite:///unused.db",
        webhook_hmac_secret="secret",
        llm_runtime_mode="deterministic",
        openai_api_key=None,
        openai_model_llm1="gpt-4o-mini",
        openai_model_llm2="gpt-4o-mini",
        log_level="INFO",
    )


class FakeMatrixRuntimeClient:
    def __init__(self) -> None:
        self._counter = 0
        self.send_calls: list[tuple[str, str]] = []
        self.reply_calls: list[tuple[str, str, str]] = []
        self.fail_room3_send_attempts = 0
        self.fail_room3_reply_attempts = 0

    def _next_event_id(self) -> str:
        self._counter += 1
        return f"$event-{self._counter}"

    async def send_text(
        self,
        *,
        room_id: str,
        body: str,
        formatted_body: str | None = None,
    ) -> str:
        _ = formatted_body
        self.send_calls.append((room_id, body))
        if room_id == "!room3:example.org" and self.fail_room3_send_attempts > 0:
            self.fail_room3_send_attempts -= 1
            raise RuntimeError("room3 send failed")
        return self._next_event_id()

    async def send_file_from_mxc(
        self,
        *,
        room_id: str,
        filename: str,
        mxc_url: str,
        mimetype: str,
    ) -> str:
        _ = room_id, filename, mxc_url, mimetype
        return self._next_event_id()

    async def reply_text(
        self,
        *,
        room_id: str,
        event_id: str,
        body: str,
        formatted_body: str | None = None,
    ) -> str:
        _ = formatted_body
        self.reply_calls.append((room_id, event_id, body))
        if room_id == "!room3:example.org" and self.fail_room3_reply_attempts > 0:
            self.fail_room3_reply_attempts -= 1
            raise RuntimeError("room3 reply failed")
        return self._next_event_id()

    async def reply_file_from_mxc(
        self,
        *,
        room_id: str,
        event_id: str,
        filename: str,
        mxc_url: str,
        mimetype: str,
    ) -> str:
        _ = room_id, event_id, filename, mxc_url, mimetype
        return self._next_event_id()

    async def redact_event(self, *, room_id: str, event_id: str) -> None:
        _ = room_id, event_id

    async def download_mxc(self, mxc_url: str) -> bytes:
        _ = mxc_url
        return b"%PDF"


async def _create_immediate_case(
    *,
    case_repo: SqlAlchemyCaseRepository,
    message_repo: SqlAlchemyMessageRepository,
    origin_event_id: str,
) -> UUID:
    case = await case_repo.create_case(
        CaseCreateInput(
            case_id=uuid4(),
            status=CaseStatus.WAIT_DOCTOR,
            room1_origin_room_id="!room1:example.org",
            room1_origin_event_id=origin_event_id,
            room1_sender_user_id="@human:example.org",
        )
    )
    await case_repo.store_pdf_extraction(
        case_id=case.case_id,
        pdf_mxc_url=f"mxc://example.org/{case.case_id}",
        extracted_text="texto extraido",
        agency_record_number="4777300",
    )
    await case_repo.store_llm1_artifacts(
        case_id=case.case_id,
        structured_data_json={
            "eda": {
                "is_pediatric": True,
                "requested_procedure": {
                    "name": "EDA para retirada de corpo estranho",
                    "subtype": "foreign_body",
                },
            },
            "patient": {
                "name": "EVALDO CARDOSO DOS SANTOS",
                "age": 12,
            },
            "policy_precheck": {"pediatric_flag": True},
        },
        summary_text="Resumo",
    )
    await case_repo.apply_doctor_decision_if_waiting(
        DoctorDecisionUpdateInput(
            case_id=case.case_id,
            doctor_user_id="@doctor:example.org",
            decision="accept",
            support_flag="anesthesist_icu",
            admission_flow="immediate",
            reason="vinda imediata autorizada",
        )
    )
    await message_repo.append_case_matrix_message_transcript(
        CaseMatrixMessageTranscriptCreateInput(
            case_id=case.case_id,
            room_id="!room2:example.org",
            event_id=f"$doctor-reply-{case.case_id}",
            sender="@doctor:example.org",
            sender_display_name="Dra. Beatriz Silva",
            message_type="room2_doctor_reply",
            message_text="decisao: aceitar",
            reply_to_event_id=f"$room2-template-{case.case_id}",
        )
    )
    return case.case_id


@pytest.mark.asyncio
async def test_runtime_immediate_branch_posts_room3_and_closes_only_on_room1_ack(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "immediate_branch_runtime_success.db")
    settings = _set_required_env(monkeypatch)
    session_factory = create_session_factory(async_url)

    case_repo = SqlAlchemyCaseRepository(session_factory)
    audit_repo = SqlAlchemyAuditRepository(session_factory)
    message_repo = SqlAlchemyMessageRepository(session_factory)
    queue_repo = SqlAlchemyJobQueueRepository(session_factory)
    matrix_client = FakeMatrixRuntimeClient()

    case_id = await _create_immediate_case(
        case_repo=case_repo,
        message_repo=message_repo,
        origin_event_id="$origin-immediate-runtime-success",
    )
    job = await queue_repo.enqueue(
        JobEnqueueInput(
            case_id=case_id,
            job_type="post_immediate_admission_flow",
            payload={},
        )
    )

    runtime = build_worker_runtime(
        settings=settings,
        session_factory=session_factory,
        matrix_client=matrix_client,
    )
    claimed_count = await runtime.run_once()

    assert claimed_count == 1
    assert len(matrix_client.send_calls) == 1
    assert len(matrix_client.reply_calls) == 2
    assert matrix_client.send_calls[0][0] == "!room3:example.org"
    assert "Vinda imediata autorizada" in matrix_client.send_calls[0][1]
    room3_replies = [call for call in matrix_client.reply_calls if call[0] == "!room3:example.org"]
    room1_replies = [call for call in matrix_client.reply_calls if call[0] == "!room1:example.org"]
    assert len(room3_replies) == 1
    assert len(room1_replies) == 1
    assert room1_replies[0][1] == "$origin-immediate-runtime-success"
    assert "aceito com vinda imediata autorizada" in room1_replies[0][2]

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        job_row = connection.execute(
            sa.text(
                "SELECT status, attempts, last_error FROM jobs WHERE job_id = :job_id"
            ),
            {"job_id": job.job_id},
        ).mappings().one()
        case_row = connection.execute(
            sa.text(
                "SELECT status, room1_final_reply_event_id FROM cases WHERE case_id = :case_id"
            ),
            {"case_id": case_id.hex},
        ).mappings().one()
        message_rows = connection.execute(
            sa.text(
                "SELECT kind, event_id FROM case_messages WHERE case_id = :case_id ORDER BY id"
            ),
            {"case_id": case_id.hex},
        ).mappings().all()
        reaction_rows = connection.execute(
            sa.text(
                "SELECT stage, target_event_id, outcome FROM case_reaction_checkpoints "
                "WHERE case_id = :case_id ORDER BY stage"
            ),
            {"case_id": case_id.hex},
        ).mappings().all()
        room3_scheduling_count = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM case_messages WHERE case_id = :case_id "
                "AND kind IN ('room3_request', 'room3_template')"
            ),
            {"case_id": case_id.hex},
        ).scalar_one()

    assert job_row["status"] == "done"
    assert int(job_row["attempts"]) == 0
    assert job_row["last_error"] is None
    assert case_row["status"] == "WAIT_R1_CLEANUP_THUMBS"
    assert case_row["room1_final_reply_event_id"] == message_rows[2]["event_id"]
    assert [row["kind"] for row in message_rows] == [
        "room3_immediate_info",
        "room3_immediate_ack",
        "room1_final",
    ]
    assert int(room3_scheduling_count) == 0
    assert [dict(row) for row in reaction_rows] == [
        {
            "stage": "ROOM1_FINAL",
            "target_event_id": message_rows[2]["event_id"],
            "outcome": "PENDING",
        },
        {
            "stage": "ROOM3_ACK",
            "target_event_id": message_rows[1]["event_id"],
            "outcome": "PENDING",
        },
    ]

    reaction_service = ReactionService(
        room1_id="!room1:example.org",
        room2_id="!room2:example.org",
        room3_id="!room3:example.org",
        case_repository=case_repo,
        audit_repository=audit_repo,
        message_repository=message_repo,
        job_queue=queue_repo,
        reaction_checkpoint_repository=SqlAlchemyReactionCheckpointRepository(session_factory),
    )

    room3_result = await reaction_service.handle(
        ReactionEvent(
            room_id="!room3:example.org",
            reaction_event_id="$reaction-room3-immediate-success",
            reactor_user_id="@scheduler:example.org",
            reactor_display_name="Enf. Maria",
            related_event_id=str(message_rows[1]["event_id"]),
            reaction_key="👍",
        )
    )
    assert room3_result.processed is True

    with engine.begin() as connection:
        room3_case_row = connection.execute(
            sa.text("SELECT status FROM cases WHERE case_id = :case_id"),
            {"case_id": case_id.hex},
        ).mappings().one()
        cleanup_jobs_before_room1 = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM jobs "
                "WHERE case_id = :case_id AND job_type = 'execute_cleanup'"
            ),
            {"case_id": case_id.hex},
        ).scalar_one()
        room3_checkpoint = connection.execute(
            sa.text(
                "SELECT outcome, reactor_user_id FROM case_reaction_checkpoints "
                "WHERE case_id = :case_id AND stage = 'ROOM3_ACK'"
            ),
            {"case_id": case_id.hex},
        ).mappings().one()

    assert room3_case_row["status"] == "WAIT_R1_CLEANUP_THUMBS"
    assert int(cleanup_jobs_before_room1) == 0
    assert room3_checkpoint == {
        "outcome": "POSITIVE_RECEIVED",
        "reactor_user_id": "@scheduler:example.org",
    }

    room1_result = await reaction_service.handle(
        ReactionEvent(
            room_id="!room1:example.org",
            reaction_event_id="$reaction-room1-immediate-success",
            reactor_user_id="@nurse:example.org",
            reactor_display_name="Enf. Ana",
            related_event_id=str(message_rows[2]["event_id"]),
            reaction_key="✅",
        )
    )
    assert room1_result.processed is True

    with engine.begin() as connection:
        final_case_row = connection.execute(
            sa.text(
                "SELECT status, cleanup_triggered_at FROM cases WHERE case_id = :case_id"
            ),
            {"case_id": case_id.hex},
        ).mappings().one()
        cleanup_jobs_after_room1 = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM jobs "
                "WHERE case_id = :case_id AND job_type = 'execute_cleanup'"
            ),
            {"case_id": case_id.hex},
        ).scalar_one()

    assert final_case_row["status"] == "CLEANUP_RUNNING"
    assert final_case_row["cleanup_triggered_at"] is not None
    assert int(cleanup_jobs_after_room1) == 1


@pytest.mark.asyncio
async def test_runtime_immediate_branch_tolerates_room3_ack_failure_and_retry_is_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "immediate_branch_runtime_retry.db")
    settings = _set_required_env(monkeypatch)
    session_factory = create_session_factory(async_url)

    case_repo = SqlAlchemyCaseRepository(session_factory)
    message_repo = SqlAlchemyMessageRepository(session_factory)
    queue_repo = SqlAlchemyJobQueueRepository(session_factory)
    matrix_client = FakeMatrixRuntimeClient()
    matrix_client.fail_room3_reply_attempts = 1

    case_id = await _create_immediate_case(
        case_repo=case_repo,
        message_repo=message_repo,
        origin_event_id="$origin-immediate-runtime-retry",
    )
    first_job = await queue_repo.enqueue(
        JobEnqueueInput(
            case_id=case_id,
            job_type="post_immediate_admission_flow",
            payload={},
        )
    )

    runtime = build_worker_runtime(
        settings=settings,
        session_factory=session_factory,
        matrix_client=matrix_client,
    )
    first_claimed = await runtime.run_once()

    assert first_claimed == 1

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        first_job_row = connection.execute(
            sa.text("SELECT status, attempts, last_error FROM jobs WHERE job_id = :job_id"),
            {"job_id": first_job.job_id},
        ).mappings().one()
        first_case_row = connection.execute(
            sa.text(
                "SELECT status, room1_final_reply_event_id FROM cases WHERE case_id = :case_id"
            ),
            {"case_id": case_id.hex},
        ).mappings().one()
        first_message_rows = connection.execute(
            sa.text(
                "SELECT kind FROM case_messages WHERE case_id = :case_id ORDER BY id"
            ),
            {"case_id": case_id.hex},
        ).scalars().all()

    assert first_job_row["status"] == "done"
    assert int(first_job_row["attempts"]) == 0
    assert first_job_row["last_error"] is None
    assert first_case_row["status"] == "WAIT_R1_CLEANUP_THUMBS"
    assert first_case_row["room1_final_reply_event_id"] is not None
    assert list(first_message_rows) == ["room3_immediate_info", "room1_final"]

    second_job = await queue_repo.enqueue(
        JobEnqueueInput(
            case_id=case_id,
            job_type="post_immediate_admission_flow",
            payload={},
        )
    )
    second_claimed = await runtime.run_once()

    assert second_claimed == 1

    with engine.begin() as connection:
        second_job_row = connection.execute(
            sa.text("SELECT status, attempts, last_error FROM jobs WHERE job_id = :job_id"),
            {"job_id": second_job.job_id},
        ).mappings().one()
        final_case_row = connection.execute(
            sa.text(
                "SELECT status, room1_final_reply_event_id FROM cases WHERE case_id = :case_id"
            ),
            {"case_id": case_id.hex},
        ).mappings().one()
        final_message_rows = connection.execute(
            sa.text(
                "SELECT kind FROM case_messages WHERE case_id = :case_id ORDER BY id"
            ),
            {"case_id": case_id.hex},
        ).scalars().all()
        room1_final_count = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM case_messages "
                "WHERE case_id = :case_id AND kind = 'room1_final'"
            ),
            {"case_id": case_id.hex},
        ).scalar_one()
        room3_ack_count = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM case_messages "
                "WHERE case_id = :case_id AND kind = 'room3_immediate_ack'"
            ),
            {"case_id": case_id.hex},
        ).scalar_one()
        room3_info_count = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM case_messages "
                "WHERE case_id = :case_id AND kind = 'room3_immediate_info'"
            ),
            {"case_id": case_id.hex},
        ).scalar_one()
        room3_scheduling_count = connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM case_messages WHERE case_id = :case_id "
                "AND kind IN ('room3_request', 'room3_template')"
            ),
            {"case_id": case_id.hex},
        ).scalar_one()

    assert second_job_row["status"] == "done"
    assert int(second_job_row["attempts"]) == 0
    assert second_job_row["last_error"] is None
    assert final_case_row["status"] == "WAIT_R1_CLEANUP_THUMBS"
    assert final_case_row["room1_final_reply_event_id"] is not None
    assert list(final_message_rows) == [
        "room3_immediate_info",
        "room1_final",
        "room3_immediate_ack",
    ]
    assert int(room1_final_count) == 1
    assert int(room3_ack_count) == 1
    assert int(room3_info_count) == 1
    assert int(room3_scheduling_count) == 0
