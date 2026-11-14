"""Blocking provider calls (filter LLM, Pinecone rerank) must run in a worker
thread, not on the single uvicorn event loop (security audit run-1)."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app


def _not_on_event_loop() -> bool:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return True
    return False


def test_plan_retrieval_runs_off_the_event_loop():
    seen = []

    def fake_plan(session_id, message):
        seen.append(_not_on_event_loop())
        raise RuntimeError("stop after the check")

    with patch("api.routes.chat._plan_retrieval", side_effect=fake_plan):
        TestClient(app).post("/chat", json={"message": "food security in Sudan"})
        TestClient(app).post("/chat/stream", json={"message": "food security in Sudan"})
    assert seen == [True, True]


def test_chat_rerank_runs_off_the_event_loop():
    from api.routes import chat
    seen = []

    def fake_rerank(query, docs, k):
        seen.append(_not_on_event_loop())
        return docs

    retriever = MagicMock()
    retriever.ainvoke = AsyncMock(return_value=[])
    with patch.object(chat, "build_retriever", return_value=retriever), \
         patch.object(chat, "rerank_by_relevance", side_effect=fake_rerank):
        asyncio.run(chat._retrieve_docs("q", {}))
    assert seen and all(seen)


def test_report_rerank_runs_off_the_event_loop():
    from rag import report_service
    seen = []

    def fake_rerank(query, docs, k):
        seen.append(_not_on_event_loop())
        return docs

    retriever = MagicMock()
    retriever.ainvoke = AsyncMock(return_value=[])
    with patch.object(report_service, "build_retriever", return_value=retriever), \
         patch.object(report_service, "rerank_by_relevance", side_effect=fake_rerank):
        asyncio.run(report_service.retrieve_for_report("Sudan", None, None, None))
    assert seen == [True]
