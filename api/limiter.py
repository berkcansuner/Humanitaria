"""Shared per-client-IP rate limiter.

Lives in its own module so both the chat and auth route packages can import the
SAME limiter instance without a circular dependency: chat.py imports
``auth.get_current_user``, so auth.py must not import from chat.py.

The instance is registered on ``app.state.limiter`` in api.main, where the 429
handler is also installed. Routes throttle with ``@limiter.limit(<callable>)``.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
