"""Service for executing case cleanup via Matrix redactions."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from triage_automation.application.ports.audit_repository_port import (
    AuditEventCreateInput,
    AuditRepositoryPort,
)
from triage_automation.application.ports.case_repository_port import CaseRepositoryPort
from triage_automation.application.ports.message_repository_port import MessageRepositoryPort

logger = logging.getLogger(__name__)
_MIN_RETRY_DELAY_SECONDS = 0.2
_RETRY_AFTER_PATTERN = re.compile(r'"retry_after_ms"\s*:\s*(\d+)', flags=re.IGNORECASE)


class MatrixRedactorPort(Protocol):
    """Port used to redact Matrix events during cleanup execution."""

    async def redact_event(self, *, room_id: str, event_id: str) -> None:
        """Redact an event in a room."""


@dataclass(frozen=True)
class ExecuteCleanupResult:
    """Outcome model for cleanup execution job."""

    redacted_success: int
    redacted_failed: int


class ExecuteCleanupService:
    """Redact all case messages and finalize cleanup state."""

    def __init__(
        self,
        *,
        case_repository: CaseRepositoryPort,
        audit_repository: AuditRepositoryPort,
        message_repository: MessageRepositoryPort,
        matrix_redactor: MatrixRedactorPort,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        max_redaction_attempts: int = 5,
    ) -> None:
        self._case_repository = case_repository
        self._audit_repository = audit_repository
        self._message_repository = message_repository
        self._matrix_redactor = matrix_redactor
        self._sleep = sleep
        self._max_redaction_attempts = max(1, max_redaction_attempts)

    async def execute(self, *, case_id: UUID) -> ExecuteCleanupResult:
        """Redact all tracked case messages and mark case CLEANED."""

        logger.info("cleanup_started case_id=%s", case_id)
        refs = await self._message_repository.list_message_refs_for_case(case_id=case_id)
        logger.info("cleanup_refs_loaded case_id=%s message_refs=%s", case_id, len(refs))

        success_count = 0
        failed_count = 0

        for ref in refs:
            try:
                await self._redact_with_retry(
                    case_id=case_id,
                    room_id=ref.room_id,
                    event_id=ref.event_id,
                )
            except Exception as error:  # noqa: BLE001
                failed_count += 1
                logger.warning(
                    "cleanup_redaction_failed case_id=%s room_id=%s event_id=%s error=%s",
                    case_id,
                    ref.room_id,
                    ref.event_id,
                    error,
                )
                await self._audit_repository.append_event(
                    AuditEventCreateInput(
                        case_id=case_id,
                        actor_type="system",
                        room_id=ref.room_id,
                        matrix_event_id=ref.event_id,
                        event_type="MATRIX_EVENT_REDACTION_FAILED",
                        payload={"error": str(error)},
                    )
                )
                continue

            success_count += 1
            logger.info(
                "cleanup_redaction_ok case_id=%s room_id=%s event_id=%s",
                case_id,
                ref.room_id,
                ref.event_id,
            )
            await self._audit_repository.append_event(
                AuditEventCreateInput(
                    case_id=case_id,
                    actor_type="system",
                    room_id=ref.room_id,
                    matrix_event_id=ref.event_id,
                    event_type="MATRIX_EVENT_REDACTED",
                    payload={},
                )
            )

        await self._case_repository.mark_cleanup_completed(case_id=case_id)
        await self._audit_repository.append_event(
            AuditEventCreateInput(
                case_id=case_id,
                actor_type="system",
                event_type="CLEANUP_COMPLETED",
                payload={
                    "count_redacted_success": success_count,
                    "count_redacted_failed": failed_count,
                },
            )
        )

        logger.info(
            "cleanup_completed case_id=%s redacted_success=%s redacted_failed=%s",
            case_id,
            success_count,
            failed_count,
        )
        return ExecuteCleanupResult(
            redacted_success=success_count,
            redacted_failed=failed_count,
        )

    async def _redact_with_retry(
        self,
        *,
        case_id: UUID,
        room_id: str,
        event_id: str,
    ) -> None:
        """Redact one Matrix event with rate-limit aware retries."""

        for attempt in range(1, self._max_redaction_attempts + 1):
            try:
                await self._matrix_redactor.redact_event(room_id=room_id, event_id=event_id)
                return
            except Exception as error:  # noqa: BLE001
                retry_delay_seconds = _extract_retry_delay_seconds(error)
                if retry_delay_seconds is None or attempt >= self._max_redaction_attempts:
                    raise
                logger.warning(
                    (
                        "cleanup_redaction_rate_limited case_id=%s room_id=%s event_id=%s "
                        "attempt=%s max_attempts=%s retry_after_s=%.3f"
                    ),
                    case_id,
                    room_id,
                    event_id,
                    attempt,
                    self._max_redaction_attempts,
                    retry_delay_seconds,
                )
                await self._sleep(retry_delay_seconds)


def _extract_retry_delay_seconds(error: Exception) -> float | None:
    """Extract Matrix retry delay from 429 error payload when available."""

    status_code = getattr(error, "status_code", None)
    if isinstance(status_code, int) and status_code != 429:
        return None

    details = getattr(error, "details", None)
    retry_after_ms = _extract_retry_after_ms_from_text(str(details) if details is not None else "")
    if retry_after_ms is None:
        retry_after_ms = _extract_retry_after_ms_from_text(str(error))

    if retry_after_ms is None:
        if isinstance(status_code, int) and status_code == 429:
            return _MIN_RETRY_DELAY_SECONDS
        return None
    return max(_MIN_RETRY_DELAY_SECONDS, retry_after_ms / 1000.0)


def _extract_retry_after_ms_from_text(text: str) -> int | None:
    """Extract `retry_after_ms` value from JSON or raw text snippets."""

    if not text:
        return None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            retry_value = parsed.get("retry_after_ms")
            if isinstance(retry_value, int):
                return retry_value
    except json.JSONDecodeError:
        pass

    match = _RETRY_AFTER_PATTERN.search(text)
    if match is None:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None
