"""Raw-body HMAC authentication helpers for webhook callbacks."""

from __future__ import annotations

import hashlib
import hmac


def compute_hmac_sha256(*, secret: str, body: bytes) -> str:
    """Return hex HMAC-SHA256 digest for raw request body."""

    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256)
    return digest.hexdigest()


def verify_hmac_signature(*, secret: str, body: bytes, provided_signature: str | None) -> bool:
    """Validate provided signature against raw body using constant-time comparison."""

    if not provided_signature:
        return False

    normalized = provided_signature.strip().lower()
    if normalized.startswith("sha256="):
        normalized = normalized.split("=", maxsplit=1)[1]

    expected = compute_hmac_sha256(secret=secret, body=body)
    return hmac.compare_digest(expected, normalized)
