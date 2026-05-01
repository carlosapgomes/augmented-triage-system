"""Client IP resolution with trusted proxy support.

Resolves the client origin IP from a Django HTTP request, considering
only explicitly trusted proxies and rejecting forwarding headers from
untrusted sources. This module is designed to be reusable by later
access-control slices (e.g. intranet zone enforcement).

The resolution algorithm:

1. If no ``trusted_proxies`` are configured (empty list or empty settings),
   the resolver returns ``REMOTE_ADDR`` directly — no header is trusted.
2. Starting from ``REMOTE_ADDR`` (the rightmost peer), walk the
   ``X-Forwarded-For`` chain from right to left as long as each hop
   is a trusted proxy.
3. The first non-trusted IP encountered (reading right-to-left) is the
   resolved client IP.
4. If ``X-Forwarded-For`` is missing or empty, ``REMOTE_ADDR`` is returned.
"""

from collections.abc import Sequence

from django.conf import settings
from django.http import HttpRequest


def resolve_client_ip(
    request: HttpRequest,
    *,
    trusted_proxies: Sequence[str] | None = None,
) -> str:
    """Resolve the real client IP from a Django request.

    Walks the ``X-Forwarded-For`` chain from right to left, trusting
    only explicitly configured proxy addresses. The first non-trusted
    IP in the chain is returned as the client origin.

    Args:
        request: The Django HTTP request to resolve the IP from.
        trusted_proxies: Explicit list of trusted proxy IP addresses.
            If ``None``, reads ``settings.TRUSTED_PROXIES`` (default: empty).

    Returns:
        The resolved client IP address as a string.
    """
    remote_addr: str = request.META.get("REMOTE_ADDR", "")

    # Determine which proxies to trust
    if trusted_proxies is None:
        trusted_proxies = getattr(settings, "TRUSTED_PROXIES", [])

    # Convert to a set for fast membership checks
    trusted_set = frozenset(trusted_proxies)

    # If no trusted proxies configured, always return REMOTE_ADDR
    if not trusted_set:
        return remote_addr

    # If REMOTE_ADDR itself is not trusted, ignore forwarding headers
    if remote_addr not in trusted_set:
        return remote_addr

    # Parse X-Forwarded-For chain
    xff: str = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if not xff:
        return remote_addr

    # Split and clean IPs (left-to-right order in the header)
    forwarded_ips: list[str] = [ip.strip() for ip in xff.split(",")]
    forwarded_ips = [ip for ip in forwarded_ips if ip]

    if not forwarded_ips:
        return remote_addr

    # Walk from right to left: skip all trusted proxies
    # The chain is: client, proxy1, proxy2, ...
    # REMOTE_ADDR is the direct peer (rightmost proxy).
    # We need to find the rightmost IP that is NOT a trusted proxy.
    for ip_str in reversed(forwarded_ips):
        if ip_str not in trusted_set:
            return ip_str

    # All forwarded IPs are trusted proxies — fall back to the leftmost
    return forwarded_ips[0]
