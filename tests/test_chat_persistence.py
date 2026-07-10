"""Chat flow persists exchanges to SQLite and re-seeds the window on a cold
request (e.g. after a restart)."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    settings = MagicMock()
    settings.DATABASE_URL = ""
    settings.CONVERSATION_DB_PATH = str(tmp_path / "conversations.db")
    with patch("rag.db.get_settings", return_value=settings):
        from api.main import app
        yield TestClient(app)


def _patched_chat_deps():
    """Patch the chat route's heavy deps with cheap stand-ins. Returns the
    context managers to enter."""
    doc = MagicMock()
    doc.page_content = "İçerik"
    doc.metadata = {"title": "Doc", "url": "http://example.com/1"}
    retriever = MagicMock()
    retriever.ainvoke = AsyncMock(return_value=[doc])

    async def astream(*args, **kwargs):
        yield "Cevap [1]."

    chain = MagicMock()
    chain.astream = astream

    return [
        patch("api.routes.chat.extract_filters", return_value={}),
        patch("api.routes.chat.analyze_query", return_value={"is_vague": False}),
        patch("api.routes.chat.build_retriever", return_value=retriever),
        patch("api.routes.chat.build_chain", return_value=chain),
        # rerank/dedupe/date helpers are pass-throughs over our single doc
        patch("api.routes.chat.apply_date_filter", side_effect=lambda d, f: d),
        patch("api.routes.chat.dedupe_by_document", side_effect=lambda d: d),
        patch("api.routes.chat.rerank_by_relevance", side_effect=lambda q, d, k: d),
        patch("api.routes.chat.rerank_by_recency", side_effect=lambda d, decay_factor=None: d),
    ]


def test_stream_persists_conversation_and_messages(client, test_user_id):
    from rag import conversations as store
    patches = _patched_chat_deps()
    for p in patches:
        p.start()
    try:
        r = client.post("/chat/stream", json={"message": "Soru nedir?", "session_id": "conv-1"})
        assert r.status_code == 200
        _ = r.text  # consume the stream so the generator finishes + persists
    finally:
        for p in patches:
            p.stop()

    assert store.conversation_exists("conv-1")
    msgs = store.get_messages("conv-1")
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[0]["content"] == "Soru nedir?"
    # title derived from the first user message
    assert store.list_conversations(test_user_id)[0]["title"] == "Soru nedir?"


def test_cold_request_seeds_window_from_sqlite(client):
    from rag import conversations as store
    from rag.history import _session_histories

    patches = _patched_chat_deps()
    for p in patches:
        p.start()
    try:
        client.post("/chat/stream", json={"message": "İlk soru", "session_id": "conv-2"}).text
        # Simulate a restart: the in-memory window is gone but SQLite persists.
        _session_histories.clear()

        with patch("api.routes.chat.populate_history_from_messages") as seed:
            client.post("/chat/stream", json={"message": "İkinci soru", "session_id": "conv-2"}).text
            # Seeded once from the 2 persisted messages of the first exchange.
            assert seed.call_count == 1
            seeded_msgs = seed.call_args.args[1]
            assert len(seeded_msgs) == 2
    finally:
        for p in patches:
            p.stop()

    # Both exchanges are now persisted (4 messages total).
    assert len(store.get_messages("conv-2")) == 4
