"""Shared per-client-IP rate limiter.

Lives in its own module so both the chat and auth route packages can import the
SAME limiter instance without a circular dependency: chat.py imports
``auth.get_current_user``, so auth.py must not import from chat.py.

The instance is registered on ``app.state.limiter`` in api.main, where the 429
handler is also installed. Routes throttle with ``@limiter.limit(<callable>)``.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from config import get_settings


def _client_ip(request) -> str:
    """Rate-limit key = the real client IP.

    Behind a reverse proxy ``request.client.host`` is the proxy, so every user would
    share one bucket (a single IP could then exhaust the login/chat limit for everyone
    — audit P2-01). When ``RATE_LIMIT_TRUSTED_HOPS > 0`` we read the client IP from
    ``X-Forwarded-For``, taking the entry the trusted proxy appended (the Nth from the
    right, N = trusted hops) — spoofing-safe, since a client-supplied XFF prefix never
    reaches that position. Default 0 = trust nothing (use the socket peer)."""
    hops = get_settings().RATE_LIMIT_TRUSTED_HOPS
    if hops > 0:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            parts = [p.strip() for p in fwd.split(",") if p.strip()]
            if len(parts) >= hops:
                return parts[-hops]
    return get_remote_address(request)


limiter = Limiter(key_func=_client_ip)
