from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic.config import Config
from fastapi.testclient import TestClient

from alembic import command
from apps.bot_api.main import create_app
from triage_automation.application.services.auth_service import AuthService
from triage_automation.infrastructure.db.auth_event_repository import SqlAlchemyAuthEventRepository
from triage_automation.infrastructure.db.auth_token_repository import SqlAlchemyAuthTokenRepository
from triage_automation.infrastructure.db.session import create_session_factory
from triage_automation.infrastructure.db.user_repository import SqlAlchemyUserRepository
from triage_automation.infrastructure.security.password_hasher import BcryptPasswordHasher
from triage_automation.infrastructure.security.token_service import OpaqueTokenService


def _upgrade_head(tmp_path: Path, filename: str) -> tuple[str, str]:
    db_path = tmp_path / filename
    sync_url = f"sqlite+pysqlite:///{db_path}"
    async_url = f"sqlite+aiosqlite:///{db_path}"

    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(alembic_config, "head")
    return sync_url, async_url


def _insert_user(
    connection: sa.Connection,
    *,
    user_id: UUID,
    email: str,
    role: str,
) -> None:
    hasher = BcryptPasswordHasher()
    connection.execute(
        sa.text(
            "INSERT INTO users (id, email, password_hash, role, is_active) "
            "VALUES (:id, :email, :password_hash, :role, 1)"
        ),
        {
            "id": user_id.hex,
            "email": email,
            "password_hash": hasher.hash_password("unused-password"),
            "role": role,
        },
    )


def _insert_token(
    connection: sa.Connection,
    *,
    token_service: OpaqueTokenService,
    user_id: UUID,
    token: str,
) -> None:
    expires_at = datetime.now(tz=UTC) + timedelta(days=30)
    connection.execute(
        sa.text(
            "INSERT INTO auth_tokens (user_id, token_hash, expires_at, issued_at) "
            "VALUES (:user_id, :token_hash, :expires_at, :issued_at)"
        ),
        {
            "user_id": user_id.hex,
            "token_hash": token_service.hash_token(token),
            "expires_at": expires_at,
            "issued_at": expires_at - timedelta(hours=1),
        },
    )


def _insert_case(
    connection: sa.Connection,
    *,
    case_id: UUID,
    status: str,
    updated_at: datetime,
) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO cases ("
            "case_id, status, room1_origin_room_id, room1_origin_event_id, room1_sender_user_id, "
            "created_at, updated_at"
            ") VALUES ("
            ":case_id, :status, '!room1:example.org', :origin_event_id, '@reader:example.org', "
            ":created_at, :updated_at"
            ")"
        ),
        {
            "case_id": case_id.hex,
            "status": status,
            "origin_event_id": f"$origin-{case_id.hex}",
            "created_at": updated_at,
            "updated_at": updated_at,
        },
    )


def _insert_reaction_checkpoint(
    connection: sa.Connection,
    *,
    case_id: UUID,
    stage: str,
    room_id: str,
    target_event_id: str,
    expected_at: datetime,
    outcome: str = "PENDING",
    reaction_event_id: str | None = None,
    reactor_user_id: str | None = None,
    reactor_display_name: str | None = None,
    reaction_key: str | None = None,
    reacted_at: datetime | None = None,
) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO case_reaction_checkpoints ("
            "case_id, stage, room_id, target_event_id, expected_at, outcome, "
            "reaction_event_id, reactor_user_id, reactor_display_name, "
            "reaction_key, reacted_at"
            ") VALUES ("
            ":case_id, :stage, :room_id, :target_event_id, :expected_at, :outcome, "
            ":reaction_event_id, :reactor_user_id, :reactor_display_name, "
            ":reaction_key, :reacted_at"
            ")"
        ),
        {
            "case_id": case_id.hex,
            "stage": stage,
            "room_id": room_id,
            "target_event_id": target_event_id,
            "expected_at": expected_at,
            "outcome": outcome,
            "reaction_event_id": reaction_event_id,
            "reactor_user_id": reactor_user_id,
            "reactor_display_name": reactor_display_name,
            "reaction_key": reaction_key,
            "reacted_at": reacted_at,
        },
    )


def _build_client(async_url: str, *, token_service: OpaqueTokenService) -> TestClient:
    session_factory = create_session_factory(async_url)
    auth_service = AuthService(
        users=SqlAlchemyUserRepository(session_factory),
        auth_events=SqlAlchemyAuthEventRepository(session_factory),
        password_hasher=BcryptPasswordHasher(),
    )
    token_repository = SqlAlchemyAuthTokenRepository(session_factory)
    app = create_app(
        auth_service=auth_service,
        auth_token_repository=token_repository,
        token_service=token_service,
        database_url=async_url,
    )
    return TestClient(app)


@pytest.mark.asyncio
async def test_monitoring_case_detail_returns_unified_chronological_timeline(
    tmp_path: Path,
) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "monitoring_case_detail.db")
    token_service = OpaqueTokenService()
    reader_id = uuid4()
    reader_token = "reader-detail-token"
    case_id = uuid4()
    base = datetime(2026, 2, 18, 10, 0, 0, tzinfo=UTC)

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        _insert_user(connection, user_id=reader_id, email="reader@example.org", role="reader")
        _insert_token(
            connection,
            token_service=token_service,
            user_id=reader_id,
            token=reader_token,
        )
        _insert_case(
            connection,
            case_id=case_id,
            status="WAIT_DOCTOR",
            updated_at=base - timedelta(minutes=10),
        )
        connection.execute(
            sa.text(
                "INSERT INTO case_llm_interactions ("
                "case_id, stage, input_payload, output_payload, "
                "prompt_system_name, prompt_system_version, "
                "prompt_user_name, prompt_user_version, model_name, captured_at"
                ") VALUES ("
                ":case_id, 'LLM1', '{\"input\":\"x\"}', '{\"output\":\"y\"}', "
                "'llm1_system', 1, 'llm1_user', 1, 'gpt-4o-mini', :captured_at"
                ")"
            ),
            {
                "case_id": case_id.hex,
                "captured_at": base + timedelta(minutes=10),
            },
        )
        connection.execute(
            sa.text(
                "INSERT INTO case_report_transcripts (case_id, extracted_text, captured_at) "
                "VALUES (:case_id, :extracted_text, :captured_at)"
            ),
            {
                "case_id": case_id.hex,
                "extracted_text": "texto extraido",
                "captured_at": base,
            },
        )
        connection.execute(
            sa.text(
                "INSERT INTO case_matrix_message_transcripts ("
                "case_id, room_id, event_id, sender, sender_display_name, "
                "message_type, message_text, captured_at"
                ") VALUES ("
                ":case_id, '!room2:example.org', '$evt-1', '@doctor:example.org', "
                "'Dra. Joana', "
                "'room2_doctor_reply', 'ok', :captured_at"
                ")"
            ),
            {
                "case_id": case_id.hex,
                "captured_at": base + timedelta(minutes=20),
            },
        )

    with _build_client(async_url, token_service=token_service) as client:
        response = client.get(
            f"/monitoring/cases/{case_id}",
            headers={"Authorization": f"Bearer {reader_token}"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["case_id"] == str(case_id)
    assert payload["status"] == "WAIT_DOCTOR"
    assert [item["source"] for item in payload["timeline"]] == ["pdf", "llm", "matrix"]
    assert [item["channel"] for item in payload["timeline"]] == [
        "pdf",
        "llm",
        "!room2:example.org",
    ]
    assert [item["event_type"] for item in payload["timeline"]] == [
        "pdf_report_extracted",
        "LLM1",
        "room2_doctor_reply",
    ]
    assert [item["actor"] for item in payload["timeline"]] == [
        "system",
        "llm",
        "Dra. Joana",
    ]
    assert all(isinstance(item["timestamp"], str) for item in payload["timeline"])


@pytest.mark.asyncio
async def test_monitoring_case_detail_returns_not_found_for_unknown_case(tmp_path: Path) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "monitoring_case_detail_not_found.db")
    token_service = OpaqueTokenService()
    reader_id = uuid4()
    reader_token = "reader-detail-not-found"
    unknown_case_id = uuid4()

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        _insert_user(connection, user_id=reader_id, email="reader@example.org", role="reader")
        _insert_token(
            connection,
            token_service=token_service,
            user_id=reader_id,
            token=reader_token,
        )

    with _build_client(async_url, token_service=token_service) as client:
        response = client.get(
            f"/monitoring/cases/{unknown_case_id}",
            headers={"Authorization": f"Bearer {reader_token}"},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "case not found"}


@pytest.mark.asyncio
async def test_monitoring_case_detail_includes_reaction_checkpoint_events(
    tmp_path: Path,
) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "monitoring_case_detail_reactions.db")
    token_service = OpaqueTokenService()
    reader_id = uuid4()
    reader_token = "reader-detail-reaction-events"
    case_id = uuid4()
    base = datetime(2026, 2, 18, 12, 0, 0, tzinfo=UTC)

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        _insert_user(connection, user_id=reader_id, email="reader@example.org", role="reader")
        _insert_token(
            connection,
            token_service=token_service,
            user_id=reader_id,
            token=reader_token,
        )
        _insert_case(
            connection,
            case_id=case_id,
            status="WAIT_R1_CLEANUP_THUMBS",
            updated_at=base + timedelta(minutes=5),
        )
        _insert_reaction_checkpoint(
            connection,
            case_id=case_id,
            stage="ROOM2_ACK",
            room_id="!room2:example.org",
            target_event_id="$room2-ack-1",
            expected_at=base,
        )
        _insert_reaction_checkpoint(
            connection,
            case_id=case_id,
            room_id="!room2:example.org",
            stage="ROOM2_ACK",
            target_event_id="$room2-ack-2",
            expected_at=base + timedelta(minutes=2),
            outcome="POSITIVE_RECEIVED",
            reaction_event_id="$reaction-room2-1",
            reactor_user_id="@doctor:example.org",
            reactor_display_name="Dra. Joana",
            reaction_key="👍",
            reacted_at=base + timedelta(minutes=4),
        )

    with _build_client(async_url, token_service=token_service) as client:
        response = client.get(
            f"/monitoring/cases/{case_id}",
            headers={"Authorization": f"Bearer {reader_token}"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["case_id"] == str(case_id)
    assert payload["status"] == "WAIT_R1_CLEANUP_THUMBS"
    assert [item["event_type"] for item in payload["timeline"]] == [
        "ROOM2_ACK_POSITIVE_EXPECTED",
        "ROOM2_ACK_POSITIVE_EXPECTED",
        "ROOM2_ACK_POSITIVE_RECEIVED",
    ]
    assert [item["actor"] for item in payload["timeline"]] == [
        "system",
        "system",
        "Dra. Joana",
    ]
    assert [item["channel"] for item in payload["timeline"]] == [
        "!room2:example.org",
        "!room2:example.org",
        "!room2:example.org",
    ]


@pytest.mark.asyncio
async def test_monitoring_case_detail_includes_ack_and_human_reply_as_distinct_events(
    tmp_path: Path,
) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "monitoring_case_detail_ack_human.db")
    token_service = OpaqueTokenService()
    reader_id = uuid4()
    reader_token = "reader-detail-ack-human"
    case_id = uuid4()
    base = datetime(2026, 2, 18, 11, 0, 0, tzinfo=UTC)

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        _insert_user(connection, user_id=reader_id, email="reader@example.org", role="reader")
        _insert_token(
            connection,
            token_service=token_service,
            user_id=reader_id,
            token=reader_token,
        )
        _insert_case(
            connection,
            case_id=case_id,
            status="WAIT_DOCTOR",
            updated_at=base - timedelta(minutes=30),
        )
        connection.execute(
            sa.text(
                "INSERT INTO case_matrix_message_transcripts ("
                "case_id, room_id, event_id, sender, message_type, message_text, captured_at"
                ") VALUES "
                "(:case_id, '!room1:example.org', '$evt-ack', 'bot', 'bot_processing', "
                "'processando...', :ack_ts), "
                "(:case_id, '!room2:example.org', '$evt-reply', '@doctor:example.org', "
                "'room2_doctor_reply', 'decisao: aceitar', :reply_ts)"
            ),
            {
                "case_id": case_id.hex,
                "ack_ts": base,
                "reply_ts": base + timedelta(minutes=5),
            },
        )

    with _build_client(async_url, token_service=token_service) as client:
        response = client.get(
            f"/monitoring/cases/{case_id}",
            headers={"Authorization": f"Bearer {reader_token}"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert [item["event_type"] for item in payload["timeline"]] == [
        "bot_processing",
        "room2_doctor_reply",
    ]
    assert [item["actor"] for item in payload["timeline"]] == ["bot", "@doctor:example.org"]
    assert [item["channel"] for item in payload["timeline"]] == [
        "!room1:example.org",
        "!room2:example.org",
    ]


@pytest.mark.asyncio
async def test_monitoring_case_detail_includes_web_human_events_in_chronological_order(
    tmp_path: Path,
) -> None:
    """Timeline includes web-origin NIR/doctor/scheduler events with distinct source."""
    sync_url, async_url = _upgrade_head(tmp_path, "monitoring_case_detail_web_events.db")
    token_service = OpaqueTokenService()
    reader_id = uuid4()
    reader_token = "reader-detail-web-events"
    case_id = uuid4()
    base = datetime(2026, 3, 15, 9, 0, 0, tzinfo=UTC)

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        _insert_user(connection, user_id=reader_id, email="reader@example.org", role="reader")
        _insert_token(
            connection,
            token_service=token_service,
            user_id=reader_id,
            token=reader_token,
        )
        _insert_case(
            connection,
            case_id=case_id,
            status="CLEANED",
            updated_at=base + timedelta(minutes=40),
        )
        # PDF event
        connection.execute(
            sa.text(
                "INSERT INTO case_report_transcripts (case_id, extracted_text, captured_at) "
                "VALUES (:case_id, 'pdf text', :captured_at)"
            ),
            {"case_id": case_id.hex, "captured_at": base},
        )
        # Web NIR PDF upload
        connection.execute(
            sa.text(
                "INSERT INTO case_events ("
                "case_id, actor_type, event_type, actor_user_id, payload, ts"
                ") VALUES ("
                ":case_id, 'web_human', 'NIR_PDF_UPLOAD', 'nir-1', "
                ":payload, :ts"
                ")"
            ),
            {
                "case_id": case_id.hex,
                "payload": '{"origin":"web","actor":"nir@example.com",'
                '"summary_text":"PDF uploaded via web"}',
                "ts": base + timedelta(minutes=1),
            },
        )
        # Web doctor decision
        connection.execute(
            sa.text(
                "INSERT INTO case_events ("
                "case_id, actor_type, event_type, actor_user_id, payload, ts"
                ") VALUES ("
                ":case_id, 'web_human', 'DOCTOR_DECISION', 'doc-1', "
                ":payload, :ts"
                ")"
            ),
            {
                "case_id": case_id.hex,
                "payload": '{"origin":"web","actor":"doctor@example.com",'
                '"summary_text":"Decision: accept"}',
                "ts": base + timedelta(minutes=10),
            },
        )
        # Web scheduler confirmation
        connection.execute(
            sa.text(
                "INSERT INTO case_events ("
                "case_id, actor_type, event_type, actor_user_id, payload, ts"
                ") VALUES ("
                ":case_id, 'web_human', 'SCHEDULER_CONFIRMATION', 'sched-1', "
                ":payload, :ts"
                ")"
            ),
            {
                "case_id": case_id.hex,
                "payload": '{"origin":"web","actor":"scheduler@example.com",'
                '"summary_text":"Appointment confirmed"}',
                "ts": base + timedelta(minutes=20),
            },
        )
        # Web NIR final acknowledgment
        connection.execute(
            sa.text(
                "INSERT INTO case_events ("
                "case_id, actor_type, event_type, actor_user_id, payload, ts"
                ") VALUES ("
                ":case_id, 'web_human', 'NIR_FINAL_ACKNOWLEDGMENT', 'nir-1', "
                ":payload, :ts"
                ")"
            ),
            {
                "case_id": case_id.hex,
                "payload": '{"origin":"web","actor":"nir@example.com",'
                '"summary_text":"Final result acknowledged"}',
                "ts": base + timedelta(minutes=30),
            },
        )

    with _build_client(async_url, token_service=token_service) as client:
        response = client.get(
            f"/monitoring/cases/{case_id}",
            headers={"Authorization": f"Bearer {reader_token}"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["case_id"] == str(case_id)
    timeline = payload["timeline"]
    # Timeline must include web events alongside PDF
    assert len(timeline) == 5
    # Verify chronological order
    timestamps = [item["timestamp"] for item in timeline]
    assert timestamps == sorted(timestamps)
    # Verify sources
    sources = [item["source"] for item in timeline]
    assert "web" in sources
    assert "pdf" in sources
    # Verify web event types are distinguishable
    event_types = [item["event_type"] for item in timeline]
    assert "NIR_PDF_UPLOAD" in event_types
    assert "DOCTOR_DECISION" in event_types
    assert "SCHEDULER_CONFIRMATION" in event_types
    assert "NIR_FINAL_ACKNOWLEDGMENT" in event_types
    # Verify web events have distinct actor metadata
    web_items = [item for item in timeline if item["source"] == "web"]
    assert len(web_items) == 4
    actors = [item["actor"] for item in web_items]
    assert "nir@example.com" in actors
    assert "doctor@example.com" in actors
    assert "scheduler@example.com" in actors


@pytest.mark.asyncio
async def test_monitoring_case_detail_web_events_distinguishable_from_matrix(
    tmp_path: Path,
) -> None:
    """Web source/actor are distinguishable from matrix events in mixed timeline."""
    sync_url, async_url = _upgrade_head(tmp_path, "monitoring_case_detail_mixed_origin.db")
    token_service = OpaqueTokenService()
    reader_id = uuid4()
    reader_token = "reader-detail-mixed-origin"
    case_id = uuid4()
    base = datetime(2026, 3, 16, 10, 0, 0, tzinfo=UTC)

    engine = sa.create_engine(sync_url)
    with engine.begin() as connection:
        _insert_user(connection, user_id=reader_id, email="reader@example.org", role="reader")
        _insert_token(
            connection,
            token_service=token_service,
            user_id=reader_id,
            token=reader_token,
        )
        _insert_case(
            connection,
            case_id=case_id,
            status="CLEANED",
            updated_at=base + timedelta(minutes=25),
        )
        # Matrix event
        connection.execute(
            sa.text(
                "INSERT INTO case_matrix_message_transcripts ("
                "case_id, room_id, event_id, sender, sender_display_name, "
                "message_type, message_text, captured_at"
                ") VALUES ("
                ":case_id, '!room2:example.org', '$evt-1', '@doctor:matrix.org', "
                "'Dr. Matrix', 'room2_doctor_reply', 'ok', :captured_at"
                ")"
            ),
            {"case_id": case_id.hex, "captured_at": base + timedelta(minutes=5)},
        )
        # Web doctor decision (different origin, same workflow stage)
        connection.execute(
            sa.text(
                "INSERT INTO case_events ("
                "case_id, actor_type, event_type, actor_user_id, payload, ts"
                ") VALUES ("
                ":case_id, 'web_human', 'DOCTOR_DECISION', 'web-doc-1', "
                ":payload, :ts"
                ")"
            ),
            {
                "case_id": case_id.hex,
                "payload": '{"origin":"web","actor":"web-doctor@example.com",'
                '"summary_text":"Web decision: accept"}',
                "ts": base + timedelta(minutes=10),
            },
        )

    with _build_client(async_url, token_service=token_service) as client:
        response = client.get(
            f"/monitoring/cases/{case_id}",
            headers={"Authorization": f"Bearer {reader_token}"},
        )

    assert response.status_code == 200
    payload = response.json()
    timeline = payload["timeline"]
    assert len(timeline) == 2
    # Matrix event
    matrix_item = [item for item in timeline if item["source"] == "matrix"][0]
    assert matrix_item["actor"] == "Dr. Matrix"
    assert matrix_item["event_type"] == "room2_doctor_reply"
    # Web event
    web_item = [item for item in timeline if item["source"] == "web"][0]
    assert web_item["actor"] == "web-doctor@example.com"
    assert web_item["event_type"] == "DOCTOR_DECISION"
    # Both in chronological order
    assert timeline[0]["source"] == "matrix"
    assert timeline[1]["source"] == "web"
