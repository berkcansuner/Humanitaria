"""Shared pytest fixtures for RAG system tests."""
from unittest.mock import MagicMock, patch

import pytest

# Identity injected by the get_current_user override for non-real_auth tests.
_TEST_USER_ID = "test-user"


@pytest.fixture
def test_user_id():
    """The user id that owns conversations created under the auth override."""
    return _TEST_USER_ID


@pytest.fixture(autouse=True)
def _isolate_conversation_db(tmp_path):
    """Point the shared DB engine (conversations + users/sessions + reports, one
    DB) at a throwaway SQLite file for every test so the chat flow (which
    persists exchanges) and the auth store never write to the real
    ./conversations.db. Tests that need their own DB still patch
    rag.db.get_settings explicitly; that inner patch transparently overrides
    this one."""
    settings = MagicMock()
    settings.DATABASE_URL = ""
    settings.CONVERSATION_DB_PATH = str(tmp_path / "conversations.db")
    with patch("rag.db.get_settings", return_value=settings):
        yield


@pytest.fixture(autouse=True)
def _auth_override(request):
    """Authenticate route tests as a fixed test user by overriding
    get_current_user, so the many chat/conversation tests don't each have to log
    in. Tests that exercise the real cookie auth / ownership opt out with
    @pytest.mark.real_auth (the override is removed for them)."""
    from api.main import app
    from api.routes.auth import get_current_user

    if request.node.get_closest_marker("real_auth"):
        app.dependency_overrides.pop(get_current_user, None)
        yield
        return

    app.dependency_overrides[get_current_user] = lambda: {
        "id": _TEST_USER_ID,
        "email": "test@example.com",
        "name": "Test User",
    }
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def _disable_rate_limit():
    """Disable the per-IP rate limiter by default so unrelated endpoint tests
    don't trip the shared-IP limit. Tests that exercise rate limiting re-enable
    it explicitly."""
    from api.routes.chat import limiter
    previous = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = previous


@pytest.fixture
def clean_singletons():
    """Reset all module-level singletons before and after a test.

    Opt-in via: def test_foo(clean_singletons): ...
    Tests that manage their own teardown (setup_method) don't need this.
    """
    _reset()
    yield
    _reset()


def _reset():
    from rag.retriever import _get_vectorstore
    from rag.history import _session_histories
    from rag.query_processor import _llm_cache
    import rag.chain as _chain_mod
    import rag.query_processor as _qp

    _get_vectorstore.cache_clear()
    _session_histories.clear()
    _llm_cache.clear()
    _chain_mod._chain = None
    _chain_mod._report_chain = None
    _qp._llm_extractor = None
