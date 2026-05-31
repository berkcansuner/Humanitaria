"""Shared pytest fixtures for RAG system tests."""
import pytest


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
    _qp._llm_extractor = None
