from __future__ import annotations

from triage_automation.infrastructure.http.hmac_auth import (
    compute_hmac_sha256,
    verify_hmac_signature,
)


def test_valid_signature_is_accepted() -> None:
    secret = "super-secret"
    body = b'{"case_id":"123"}'
    signature = compute_hmac_sha256(secret=secret, body=body)

    assert verify_hmac_signature(secret=secret, body=body, provided_signature=signature)


def test_invalid_signature_is_rejected() -> None:
    secret = "super-secret"
    body = b'{"case_id":"123"}'

    assert not verify_hmac_signature(secret=secret, body=body, provided_signature="bad")
    assert not verify_hmac_signature(secret=secret, body=body, provided_signature=None)
