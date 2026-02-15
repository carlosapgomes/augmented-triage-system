"""Opaque token generation and hashing helpers."""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class IssuedOpaqueToken:
    """Issued token payload with persisted hash and expiration."""

    token: str
    token_hash: str
    expires_at: datetime


class OpaqueTokenService:
    """Generate opaque tokens and deterministic hashes for persistence."""

    def __init__(
        self,
        *,
        token_ttl: timedelta = timedelta(hours=8),
        token_factory: Callable[[], str] | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._token_ttl = token_ttl
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(32))
        self._now = now or (lambda: datetime.now(tz=UTC))

    def issue_token(self) -> IssuedOpaqueToken:
        """Generate opaque token and derived persisted metadata."""

        token = self._token_factory()
        return IssuedOpaqueToken(
            token=token,
            token_hash=self.hash_token(token),
            expires_at=self._now() + self._token_ttl,
        )

    def hash_token(self, token: str) -> str:
        """Hash opaque token for database storage."""

        return hashlib.sha256(token.encode("utf-8")).hexdigest()
