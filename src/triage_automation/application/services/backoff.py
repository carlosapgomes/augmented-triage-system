"""Deterministic retry backoff utilities for queue jobs."""

from __future__ import annotations

from datetime import timedelta

_BASE_SECONDS = (30, 120, 300, 600, 1200)


def compute_retry_delay(attempt: int) -> timedelta:
    """Return deterministic exponential-like delay with bounded pseudo-jitter.

    `attempt` is 1-based (first retry attempt => attempt=1).
    """

    if attempt < 1:
        raise ValueError("attempt must be >= 1")

    index = min(attempt - 1, len(_BASE_SECONDS) - 1)
    base = _BASE_SECONDS[index]

    # Deterministic jitter in [-10%, +10%] based on attempt number.
    jitter_percent = ((attempt * 37) % 21 - 10) / 100
    seconds = int(base * (1 + jitter_percent))
    return timedelta(seconds=max(1, seconds))
