"""Tests for the rate-limiter client-IP key function (P2-01).

Behind a reverse proxy, keying on request.client.host lumps every user into one
bucket (a single IP can then lock out everyone's login/chat). The key func must be
able to read the real client IP from X-Forwarded-For — but ONLY the entry the
trusted proxy appended (spoofing-safe), controlled by RATE_LIMIT_TRUSTED_HOPS.
Default 0 = trust nothing (socket peer), so untrusted deployments are unaffected.
"""
from unittest.mock import MagicMock, patch

from starlette.datastructures import Headers

from api.limiter import _client_ip


class _FakeRequest:
    def __init__(self, xff=None, client_host="10.0.0.1"):
        h = {"x-forwarded-for": xff} if xff is not None else {}
        self.headers = Headers(h)
        self.client = type("C", (), {"host": client_host})()


def _with_hops(hops):
    s = MagicMock()
    s.RATE_LIMIT_TRUSTED_HOPS = hops
    return patch("api.limiter.get_settings", return_value=s)


def test_default_no_proxy_trust_uses_socket_peer():
    with _with_hops(0):
        assert _client_ip(_FakeRequest(xff="1.2.3.4", client_host="10.0.0.1")) == "10.0.0.1"


def test_one_trusted_hop_uses_rightmost_xff_entry():
    # Client forged 9.9.9.9; the trusted proxy appended the real client 1.2.3.4.
    with _with_hops(1):
        assert _client_ip(_FakeRequest(xff="9.9.9.9, 1.2.3.4")) == "1.2.3.4"


def test_single_entry_xff_with_one_hop():
    with _with_hops(1):
        assert _client_ip(_FakeRequest(xff="1.2.3.4")) == "1.2.3.4"


def test_missing_xff_falls_back_to_socket_peer():
    with _with_hops(1):
        assert _client_ip(_FakeRequest(xff=None, client_host="10.0.0.9")) == "10.0.0.9"
