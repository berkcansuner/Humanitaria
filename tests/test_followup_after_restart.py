"""A follow-up in an existing conversation must be rewritten with its history even
when the in-memory window is cold (server restart / Render free-tier wake-up).
Before the fix the window was seeded only AFTER retrieval planning, so the first
follow-up after a restart searched the whole index with the bare follow-up text
and no filters (production: a Turkish follow-up about northern Yemen pulled
Colombia/Lebanon/Ecuador documents and was answered in Spanish)."""
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from rag import conversations as store
from rag import history


def test_cold_window_follow_up_uses_conversation_history(test_user_id):
    store.create_conversation(test_user_id, "conv-cold", "Yemen")
    store.append_message("conv-cold", "user", "Yemen'de gıda güvensizliği durumu nedir?")
    store.append_message("conv-cold", "assistant", "Yemen'de durum ciddi [1].")
    history.clear_session("conv-cold")   # simulate a restarted process

    seen = {}

    def fake_plan(message, prior):
        seen["prior"] = [m.content for m in prior]
        return "Yemen'in kuzeyinde gıda güvensizliği", {"country": "Yemen"}

    async def fake_astream(payload, *a, **k):
        yield "ok"

    doc = MagicMock(page_content="x", metadata={"title": "T", "url": "http://x"})
    with patch("api.routes.chat.plan_retrieval", side_effect=fake_plan), \
         patch("api.routes.chat.extract_filters", side_effect=AssertionError("history was ignored")), \
         patch("api.routes.chat.build_retriever", return_value=MagicMock(ainvoke=AsyncMock(return_value=[doc]))), \
         patch("api.routes.chat.build_chain", return_value=MagicMock(astream=fake_astream)):
        from api.main import app
        r = TestClient(app).post("/chat/stream", json={"message": "peki kuzeyde durum ne?",
                                                       "session_id": "conv-cold"})
    assert r.status_code == 200
    assert seen["prior"] == ["Yemen'de gıda güvensizliği durumu nedir?", "Yemen'de durum ciddi [1]."]
