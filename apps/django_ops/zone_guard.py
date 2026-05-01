"""Intranet zone guard middleware for role-based access restrictions.

Enforces that ``nir`` and ``scheduler`` roles may only access the
application from IP addresses within the configured intranet CIDR
allowlist. Denied accesses are logged with auditable evidence
including the user role and resolved client origin IP.

This middleware runs **after** Django's ``AuthenticationMiddleware``
so that ``request.user`` is available for role inspection.

Configuration (in Django settings):

- ``INTRANET_CIDR_ALLOWLIST``: list of CIDR strings defining the
  authorized intranet network (e.g. ``["10.0.0.0/8"]``).
"""

from __future__ import annotations

import ipaddress
import logging
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse

from apps.django_ops.ip_resolver import resolve_client_ip

logger = logging.getLogger(__name__)

# Roles restricted to the intranet zone.
INTRANET_ONLY_ROLES: frozenset[str] = frozenset({"nir", "scheduler"})

# Paths that bypass the zone guard entirely (login, smoke, logout, static).
BYPASS_PATH_PREFIXES: tuple[str, ...] = (
    "/login/",
    "/logout/",
    "/smoke/",
    "/static/",
)


def _is_intranet_ip(ip_str: str, cidr_allowlist: list[str]) -> bool:
    """Check whether an IP address falls within any CIDR in the allowlist.

    Args:
        ip_str: The client IP address as a string.
        cidr_allowlist: List of CIDR notation strings.

    Returns:
        ``True`` if the IP is within any allowed CIDR, ``False`` otherwise.
    """
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return any(
        addr in ipaddress.ip_network(cidr, strict=False)
        for cidr in cidr_allowlist
    )


def _should_bypass(path: str) -> bool:
    """Determine if the request path bypasses the zone guard.

    Args:
        path: The URL path of the request.

    Returns:
        ``True`` if the path should bypass zone checking.
    """
    return any(path.startswith(prefix) for prefix in BYPASS_PATH_PREFIXES)


class IntranetZoneGuardMiddleware:
    """Django middleware that restricts intranet-only roles by IP zone.

    Inspects the authenticated user's role and resolved client IP.
    If the role is in ``INTRANET_ONLY_ROLES`` and the client IP is
    outside the configured ``INTRANET_CIDR_ALLOWLIST``, the request
    is rejected with HTTP 403 and an audit log entry is emitted.

    Anonymous users, unauthenticated requests, and non-restricted roles
    pass through without interference.
    """

    def __init__(self, get_response: Any) -> None:
        """Initialize the middleware with the next response callable.

        Args:
            get_response: The next middleware or view in the chain.
        """
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process the request through the intranet zone guard.

        Args:
            request: The incoming HTTP request.

        Returns:
            Either a 403 response if access is denied, or the
            response from the downstream middleware/view.
        """
        # Skip zone check for bypass paths
        if _should_bypass(request.path):
            return self.get_response(request)

        # Only check authenticated users
        user = request.user
        if not hasattr(user, "is_authenticated") or not user.is_authenticated:
            return self.get_response(request)

        # Get the user's role
        role: str = getattr(user, "role", "")
        if role not in INTRANET_ONLY_ROLES:
            return self.get_response(request)

        # Resolve the client IP using trusted proxy rules
        client_ip = resolve_client_ip(request)

        # Get the intranet CIDR allowlist from settings
        cidr_allowlist: list[str] = getattr(
            settings, "INTRANET_CIDR_ALLOWLIST", []
        )

        # If no allowlist configured, deny by default for restricted roles
        if not cidr_allowlist:
            logger.warning(
                "zone_denial role=%s ip=%s path=%s reason=no_allowlist_configured",
                role,
                client_ip,
                request.path,
            )
            return HttpResponse(
                "Access denied: intranet-only role from unauthorized network.",
                status=403,
            )

        # Check if the IP is within the intranet CIDRs
        if _is_intranet_ip(client_ip, cidr_allowlist):
            return self.get_response(request)

        # Deny and log
        logger.warning(
            "zone_denial role=%s ip=%s path=%s reason=outside_intranet_cidr",
            role,
            client_ip,
            request.path,
        )
        return HttpResponse(
            "Access denied: intranet-only role from unauthorized network.",
            status=403,
        )
