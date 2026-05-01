"""Tests for client IP resolution with trusted proxy support.

Validates that the IP resolver correctly determines the client origin
considering trusted proxies and rejecting untrusted forwarding headers.

Scenarios:
- Direct request (no proxy) uses the real remote IP.
- Request through a trusted proxy uses the forwarded client IP.
- Request with forwarding headers from an untrusted source ignores those headers.
"""

import os

import django
import pytest
from django.test import RequestFactory

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "apps.django_ops.settings",
)
if not django.conf.settings.configured:
    django.setup()

from apps.django_ops.ip_resolver import resolve_client_ip  # noqa: E402


@pytest.fixture
def rf() -> RequestFactory:
    """Provide a Django RequestFactory for building test requests."""
    return RequestFactory()


class TestDirectRequestUsesRealIP:
    """Direct requests (no forwarding headers) use the remote IP."""

    def test_no_headers_returns_remote_addr(self, rf: RequestFactory) -> None:
        """Request without X-Forwarded-For uses REMOTE_ADDR directly."""
        request = rf.get("/", REMOTE_ADDR="10.0.0.5")
        ip = resolve_client_ip(request)
        assert ip == "10.0.0.5"

    def test_no_trusted_proxies_ignores_forwarded(self, rf: RequestFactory) -> None:
        """Without configured trusted proxies, forwarding headers are ignored."""
        request = rf.get(
            "/",
            REMOTE_ADDR="10.0.0.5",
            HTTP_X_FORWARDED_FOR="192.168.1.100",
        )
        ip = resolve_client_ip(request, trusted_proxies=[])
        assert ip == "10.0.0.5"


class TestTrustedProxyUsesForwardedIP:
    """Requests from trusted proxies use the forwarded client IP."""

    def test_single_trusted_proxy(self, rf: RequestFactory) -> None:
        """Request from a trusted proxy uses the leftmost forwarded IP."""
        request = rf.get(
            "/",
            REMOTE_ADDR="10.0.1.1",
            HTTP_X_FORWARDED_FOR="192.168.1.100",
        )
        ip = resolve_client_ip(
            request,
            trusted_proxies=["10.0.1.1"],
        )
        assert ip == "192.168.1.100"

    def test_chain_of_trusted_proxies(self, rf: RequestFactory) -> None:
        """Multiple proxies: rightmost trusted proxy determines the client IP.

        With chain: client(172.16.0.5) -> proxy1(10.0.1.1) -> proxy2(10.0.1.2)
        X-Forwarded-For: 172.16.0.5, 10.0.1.1
        REMOTE_ADDR: 10.0.1.2
        """
        request = rf.get(
            "/",
            REMOTE_ADDR="10.0.1.2",
            HTTP_X_FORWARDED_FOR="172.16.0.5, 10.0.1.1",
        )
        ip = resolve_client_ip(
            request,
            trusted_proxies=["10.0.1.1", "10.0.1.2"],
        )
        assert ip == "172.16.0.5"


class TestUntrustedProxyIgnoresForwarding:
    """Requests from untrusted sources have forwarding headers ignored."""

    def test_untrusted_proxy_ignores_xff(self, rf: RequestFactory) -> None:
        """If REMOTE_ADDR is not a trusted proxy, X-Forwarded-For is ignored."""
        request = rf.get(
            "/",
            REMOTE_ADDR="203.0.113.50",
            HTTP_X_FORWARDED_FOR="10.0.0.1",
        )
        ip = resolve_client_ip(
            request,
            trusted_proxies=["10.0.1.1"],
        )
        assert ip == "203.0.113.50"

    def test_partial_chain_only_trusts_known(self, rf: RequestFactory) -> None:
        """Only the rightmost proxies are trusted; unknown proxy breaks the chain.

        Chain: client(spoofer) -> unknown_proxy -> trusted_proxy
        X-Forwarded-For: spoofer, unknown_proxy
        REMOTE_ADDR: trusted_proxy

        Since unknown_proxy is not in trusted_proxies, we should NOT accept
        the spoofer IP from X-Forwarded-For. The result should be unknown_proxy.
        """
        request = rf.get(
            "/",
            REMOTE_ADDR="10.0.1.1",
            HTTP_X_FORWARDED_FOR="spoofer, 198.51.100.5",
        )
        ip = resolve_client_ip(
            request,
            trusted_proxies=["10.0.1.1"],
        )
        assert ip == "198.51.100.5"

    def test_spoofed_xff_from_untrusted_rejected(self, rf: RequestFactory) -> None:
        """Completely untrusted source with spoofed XFF is fully rejected."""
        request = rf.get(
            "/",
            REMOTE_ADDR="203.0.113.1",
            HTTP_X_FORWARDED_FOR="10.0.0.1, 192.168.1.1, 172.16.0.1",
        )
        ip = resolve_client_ip(
            request,
            trusted_proxies=["10.0.1.1", "10.0.1.2"],
        )
        assert ip == "203.0.113.1"


class TestEdgeCases:
    """Edge cases for IP resolution."""

    def test_empty_xff_uses_remote_addr(self, rf: RequestFactory) -> None:
        """Empty X-Forwarded-For header falls back to REMOTE_ADDR."""
        request = rf.get(
            "/",
            REMOTE_ADDR="10.0.0.5",
            HTTP_X_FORWARDED_FOR="",
        )
        ip = resolve_client_ip(
            request,
            trusted_proxies=["10.0.0.5"],
        )
        assert ip == "10.0.0.5"

    def test_xff_with_extra_spaces(self, rf: RequestFactory) -> None:
        """X-Forwarded-For with extra whitespace is trimmed correctly."""
        request = rf.get(
            "/",
            REMOTE_ADDR="10.0.1.1",
            HTTP_X_FORWARDED_FOR="  192.168.1.100  ,  10.0.1.50  ",
        )
        ip = resolve_client_ip(
            request,
            trusted_proxies=["10.0.1.1", "10.0.1.50"],
        )
        assert ip == "192.168.1.100"

    def test_default_trusted_proxies_from_settings(
        self,
        rf: RequestFactory,
    ) -> None:
        """When trusted_proxies is not provided, settings are used."""
        from django.conf import settings as django_settings

        original = getattr(django_settings, "TRUSTED_PROXIES", None)
        django_settings.TRUSTED_PROXIES = ["10.0.1.1"]
        try:
            request = rf.get(
                "/",
                REMOTE_ADDR="10.0.1.1",
                HTTP_X_FORWARDED_FOR="192.168.1.100",
            )
            ip = resolve_client_ip(request)
            assert ip == "192.168.1.100"
        finally:
            if original is None:
                del django_settings.TRUSTED_PROXIES
            else:
                django_settings.TRUSTED_PROXIES = original
