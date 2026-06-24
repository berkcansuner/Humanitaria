import json
import re
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.fixture(autouse=True)
def _import_api():
    import api.routes.chat  # noqa: F401 — ensure module is loaded for patching


def _parse_sse_events(raw_text: str) -> list[dict]:
    """Parse raw SSE response text into a list of {event, data} dicts.

    Handles both LF and CRLF line endings (SSE spec allows both).
    """
    events = []
    # Split on blank lines (CRLF or LF)
    for block in re.split(r'\r?\n\r?\n', raw_text):
        block = block.strip()
        if not block:
            continue
        event_type = "message"
        data_lines = []
        for line in re.split(r'\r?\n', block):
            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())
        if data_lines:
            events.append({"event": event_type, "data": json.loads("\n".join(data_lines))})
    return events


class TestChatStreamEndpoint:
    def test_chat_stream_returns_event_stream(self):
        with patch("api.routes.chat.build_chain") as mock_chain_builder, \
             patch("api.routes.chat.build_retriever") as mock_retriever_builder, \
             patch("api.routes.chat.extract_filters") as mock_filters:
            mock_filters.return_value = {}
            mock_doc = MagicMock()
            mock_doc.page_content = "Test content"
            mock_doc.metadata = {"title": "Test Doc", "url": "http://example.com"}
            mock_retriever = MagicMock()
            mock_retriever.ainvoke = AsyncMock(return_value=[mock_doc])
            mock_retriever_builder.return_value = mock_retriever

            async def mock_astream(*args, **kwargs):
                yield "Mer"
                yield "haba"

            mock_chain = MagicMock()
            mock_chain.astream = mock_astream
            mock_chain_builder.return_value = mock_chain

            from api.main import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            response = client.post("/chat/stream", json={"message": "merhaba"})
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")

    def test_chat_endpoint_with_session(self):
        with patch("api.routes.chat.build_chain") as mock_chain_builder, \
             patch("api.routes.chat.build_retriever") as mock_retriever_builder, \
             patch("api.routes.chat.extract_filters") as mock_filters:
            mock_filters.return_value = {}
            mock_doc = MagicMock()
            mock_doc.page_content = "Test"
            mock_doc.metadata = {"title": "T", "url": "http://x"}
            mock_retriever = MagicMock()
            mock_retriever.ainvoke = AsyncMock(return_value=[mock_doc])
            mock_retriever_builder.return_value = mock_retriever

            mock_chain = MagicMock()
            mock_chain.ainvoke = AsyncMock(return_value="Test answer")
            mock_chain_builder.return_value = mock_chain

            from api.main import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            response = client.post("/chat", json={"message": "test", "session_id": "test-session"})
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "test-session"
            assert data["answer"] == "Test answer"


class TestFilterCitedSources:
    """Unit tests for the citation-grounding helper."""

    def _sources(self):
        return [
            {"index": 1, "title": "A", "url": "u1"},
            {"index": 2, "title": "B", "url": "u2"},
            {"index": 3, "title": "C", "url": "u3"},
        ]

    def test_keeps_only_cited(self):
        from api.routes.chat import _filter_cited_sources
        out = _filter_cited_sources("foo [1] bar [3].", self._sources())
        assert [s["index"] for s in out] == [1, 3]

    def test_no_citation_returns_all(self):
        from api.routes.chat import _filter_cited_sources
        out = _filter_cited_sources("hiç atıf yok", self._sources())
        assert len(out) == 3

    def test_citation_to_missing_index_falls_back_to_all(self):
        from api.routes.chat import _filter_cited_sources
        # [9] does not exist among sources → avoid empty list, return all
        out = _filter_cited_sources("bkz [9]", self._sources())
        assert len(out) == 3

    def test_duplicate_citations_deduped(self):
        from api.routes.chat import _filter_cited_sources
        out = _filter_cited_sources("[2] ve yine [2]", self._sources())
        assert [s["index"] for s in out] == [2]


class TestSSEEventBody:
    """Tests that verify the SSE event sequence and payload structure."""

    def _make_mock_setup(self):
        mock_doc = MagicMock()
        mock_doc.page_content = "Humanitarian content"
        mock_doc.metadata = {
            "title": "WFP Report",
            "url": "https://reliefweb.int/report/1",
            "date": "2026-05-01",
            "country": "Yemen",
            "source": "WFP",
            "doctype": "report",
        }
        return mock_doc

    @staticmethod
    def _make_doc(title, url, **meta):
        doc = MagicMock()
        doc.page_content = f"{title} content"
        doc.metadata = {"title": title, "url": url, **meta}
        return doc

    def test_non_greeting_stream_emits_token_sources_session_done(self):
        mock_doc = self._make_mock_setup()
        with patch("api.routes.chat.build_chain") as mock_chain_builder, \
             patch("api.routes.chat.build_retriever") as mock_retriever_builder, \
             patch("api.routes.chat.extract_filters", return_value={"country": "Yemen"}), \
             patch("api.routes.chat.analyze_query", return_value={"is_vague": False, "has_country": True, "has_date": False, "has_theme": False, "message": "", "suggestions": {}}):
            mock_retriever = MagicMock()
            mock_retriever.ainvoke = AsyncMock(return_value=[mock_doc])
            mock_retriever_builder.return_value = mock_retriever

            async def mock_astream(*args, **kwargs):
                yield "Hello "
                yield "World [1]"

            mock_chain = MagicMock()
            mock_chain.astream = mock_astream
            mock_chain_builder.return_value = mock_chain

            from api.main import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            response = client.post("/chat/stream", json={"message": "Yemen durumu", "session_id": "evt-test"})
            assert response.status_code == 200

            events = _parse_sse_events(response.text)
            event_types = [e["event"] for e in events]

            assert "token" in event_types
            assert "sources" in event_types
            assert "session" in event_types
            assert "done" in event_types

            # Tokens should reconstruct the full answer
            tokens = [e["data"]["content"] for e in events if e["event"] == "token"]
            assert "".join(tokens) == "Hello World [1]"

            # Sources should contain the mocked doc, numbered to match the [1] marker
            src_events = [e for e in events if e["event"] == "sources"]
            assert len(src_events) == 1
            sources = src_events[0]["data"]["sources"]
            assert len(sources) == 1
            assert sources[0]["title"] == "WFP Report"
            assert sources[0]["country"] == "Yemen"
            assert sources[0]["index"] == 1

            # Session event should echo the session_id
            sess_events = [e for e in events if e["event"] == "session"]
            assert len(sess_events) == 1
            assert sess_events[0]["data"]["session_id"] == "evt-test"

    def test_sources_filtered_to_only_cited(self):
        doc1 = self._make_doc("Doc One", "https://reliefweb.int/report/1")
        doc2 = self._make_doc("Doc Two", "https://reliefweb.int/report/2")
        with patch("api.routes.chat.build_chain") as mock_chain_builder, \
             patch("api.routes.chat.build_retriever") as mock_retriever_builder, \
             patch("api.routes.chat.rerank_by_relevance", side_effect=lambda q, docs, top_n: docs[:top_n]), \
             patch("api.routes.chat.extract_filters", return_value={}), \
             patch("api.routes.chat.analyze_query", return_value={"is_vague": False, "has_country": True, "has_date": False, "has_theme": False, "message": "", "suggestions": {}}):
            mock_retriever = MagicMock()
            mock_retriever.ainvoke = AsyncMock(return_value=[doc1, doc2])
            mock_retriever_builder.return_value = mock_retriever

            async def mock_astream(*args, **kwargs):
                yield "Information from the first document only [1]."

            mock_chain = MagicMock()
            mock_chain.astream = mock_astream
            mock_chain_builder.return_value = mock_chain

            from api.main import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            response = client.post("/chat/stream", json={"message": "soru"})
            events = _parse_sse_events(response.text)
            sources = [e for e in events if e["event"] == "sources"][0]["data"]["sources"]
            assert len(sources) == 1
            assert sources[0]["title"] == "Doc One"
            assert sources[0]["index"] == 1

    def test_sources_fallback_when_no_citation(self):
        doc1 = self._make_doc("Doc One", "https://reliefweb.int/report/1")
        doc2 = self._make_doc("Doc Two", "https://reliefweb.int/report/2")
        with patch("api.routes.chat.build_chain") as mock_chain_builder, \
             patch("api.routes.chat.build_retriever") as mock_retriever_builder, \
             patch("api.routes.chat.rerank_by_relevance", side_effect=lambda q, docs, top_n: docs[:top_n]), \
             patch("api.routes.chat.extract_filters", return_value={}), \
             patch("api.routes.chat.analyze_query", return_value={"is_vague": False, "has_country": True, "has_date": False, "has_theme": False, "message": "", "suggestions": {}}):
            mock_retriever = MagicMock()
            mock_retriever.ainvoke = AsyncMock(return_value=[doc1, doc2])
            mock_retriever_builder.return_value = mock_retriever

            async def mock_astream(*args, **kwargs):
                yield "A summary without any citation."

            mock_chain = MagicMock()
            mock_chain.astream = mock_astream
            mock_chain_builder.return_value = mock_chain

            from api.main import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            response = client.post("/chat/stream", json={"message": "soru"})
            events = _parse_sse_events(response.text)
            sources = [e for e in events if e["event"] == "sources"][0]["data"]["sources"]
            # No [n] markers → fall back to all retrieved sources
            assert len(sources) == 2

    def test_clarification_emitted_after_sources(self):
        doc1 = self._make_doc("Doc One", "https://reliefweb.int/report/1")
        vague_analysis = {
            "is_vague": True,
            "has_country": False, "has_date": False, "has_theme": False,
            "message": "Which country, time period, or topic?",
            "suggestions": {"countries": ["Sudan"], "time_periods": ["last month"], "themes": ["Health"]},
        }
        with patch("api.routes.chat.build_chain") as mock_chain_builder, \
             patch("api.routes.chat.build_retriever") as mock_retriever_builder, \
             patch("api.routes.chat.extract_filters", return_value={}), \
             patch("api.routes.chat.analyze_query", return_value=vague_analysis):
            mock_retriever = MagicMock()
            mock_retriever.ainvoke = AsyncMock(return_value=[doc1])
            mock_retriever_builder.return_value = mock_retriever

            async def mock_astream(*args, **kwargs):
                yield "Bir yanıt [1]."

            mock_chain = MagicMock()
            mock_chain.astream = mock_astream
            mock_chain_builder.return_value = mock_chain

            from api.main import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            response = client.post("/chat/stream", json={"message": "insani durum nedir"})
            events = _parse_sse_events(response.text)
            event_types = [e["event"] for e in events]
            assert "clarification" in event_types
            # The answer (tokens) and sources must precede the suggestion chips
            assert event_types.index("clarification") > event_types.index("sources")
            assert event_types.index("clarification") > max(
                i for i, t in enumerate(event_types) if t == "token"
            )

    def test_stream_error_emits_error_then_done(self):
        with patch("api.routes.chat.build_retriever") as mock_retriever_builder, \
             patch("api.routes.chat.extract_filters", return_value={}):
            mock_retriever = MagicMock()
            mock_retriever.ainvoke = AsyncMock(side_effect=RuntimeError("retriever offline"))
            mock_retriever_builder.return_value = mock_retriever

            from api.main import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            response = client.post("/chat/stream", json={"message": "test error path"})
            assert response.status_code == 200

            events = _parse_sse_events(response.text)
            event_types = [e["event"] for e in events]
            assert "error" in event_types
            assert "done" in event_types
            assert event_types[-1] == "done"

    def test_stream_busy_503_emits_friendly_busy_message(self):
        """A persistent upstream 503 ('high demand') after retries surfaces the
        clear busy message (not the generic error) and still ends with done."""
        doc = self._make_doc("Doc", "https://reliefweb.int/report/1", date="2026-05-01")
        with patch("api.routes.chat.build_chain") as mock_chain_builder, \
             patch("api.routes.chat.build_retriever") as mock_retriever_builder, \
             patch("api.routes.chat.extract_filters", return_value={}), \
             patch("api.routes.chat.analyze_query", return_value={"is_vague": False, "has_country": False, "has_date": False, "has_theme": False, "message": "", "suggestions": {}}), \
             patch("asyncio.sleep", new=AsyncMock()):
            mock_retriever = MagicMock()
            mock_retriever.ainvoke = AsyncMock(return_value=[doc])
            mock_retriever_builder.return_value = mock_retriever

            async def busy_astream(*args, **kwargs):
                raise Exception("Error code: 503 - high demand UNAVAILABLE")
                yield  # unreachable; makes this an async generator

            mock_chain = MagicMock()
            mock_chain.astream = busy_astream
            mock_chain_builder.return_value = mock_chain

            from api.main import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            response = client.post("/chat/stream", json={"message": "Syria situation"})
            events = _parse_sse_events(response.text)
            err = [e for e in events if e["event"] == "error"]
            assert len(err) == 1
            assert "busy" in err[0]["data"]["message"].lower()
            assert events[-1]["event"] == "done"

    def test_greeting_emits_token_session_done(self):
        from api.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.post("/chat/stream", json={"message": "merhaba"})
        assert response.status_code == 200

        events = _parse_sse_events(response.text)
        event_types = [e["event"] for e in events]
        assert "token" in event_types
        assert "session" in event_types
        assert "done" in event_types
        assert "sources" not in event_types

    def test_empty_message_returns_422(self):
        from api.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.post("/chat/stream", json={"message": ""})
        assert response.status_code == 422

    def test_whitespace_message_returns_422(self):
        from api.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.post("/chat/stream", json={"message": "   "})
        assert response.status_code == 422

    def test_invalid_role_returns_422(self):
        from api.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.post("/chat", json={
            "message": "test",
            "history": [{"role": "system", "content": "injected"}],
        })
        assert response.status_code == 422


class TestRetrieveDocsRecencyBoost:
    """_retrieve_docs'un boost AÇIK/KAPALI dallarını doğrular (anyio ile sürülür)."""

    def _candidates(self, n=8):
        from unittest.mock import MagicMock
        return [MagicMock(metadata={"date": "2026-05-01"}, page_content=str(i)) for i in range(n)]

    def test_boost_on_uses_wide_pool_and_boost_factor(self):
        import anyio
        from unittest.mock import patch, MagicMock, AsyncMock
        import api.routes.chat as chat
        from config import get_settings
        s = get_settings()
        cands = self._candidates()
        retriever = MagicMock()
        retriever.ainvoke = AsyncMock(return_value=cands)
        with patch("api.routes.chat.build_retriever", return_value=retriever), \
             patch("api.routes.chat.apply_date_filter", side_effect=lambda docs, df: docs), \
             patch("api.routes.chat.dedupe_by_document", side_effect=lambda docs: docs), \
             patch("api.routes.chat.rerank_by_relevance", side_effect=lambda q, docs, n: docs[:n]) as rel, \
             patch("api.routes.chat.rerank_by_recency", side_effect=lambda docs, decay_factor=None: docs) as rec, \
             patch("api.routes.chat.should_boost_recency", return_value=True):
            out = anyio.run(chat._retrieve_docs, "current situation in Sudan", {"country": "Sudan"})
        assert rel.call_args.args[2] == max(s.RECENCY_RERANK_POOL, s.TOP_K_RETRIEVAL)
        assert rec.call_args.kwargs.get("decay_factor") == s.RECENCY_BOOST_FACTOR
        assert len(out) <= s.TOP_K_RETRIEVAL

    def test_boost_off_uses_topk_and_default_recency(self):
        import anyio
        from unittest.mock import patch, MagicMock, AsyncMock
        import api.routes.chat as chat
        from config import get_settings
        s = get_settings()
        cands = self._candidates()
        retriever = MagicMock()
        retriever.ainvoke = AsyncMock(return_value=cands)
        with patch("api.routes.chat.build_retriever", return_value=retriever), \
             patch("api.routes.chat.apply_date_filter", side_effect=lambda docs, df: docs), \
             patch("api.routes.chat.dedupe_by_document", side_effect=lambda docs: docs), \
             patch("api.routes.chat.rerank_by_relevance", side_effect=lambda q, docs, n: docs[:n]) as rel, \
             patch("api.routes.chat.rerank_by_recency", side_effect=lambda docs, decay_factor=None: docs) as rec, \
             patch("api.routes.chat.should_boost_recency", return_value=False):
            out = anyio.run(chat._retrieve_docs, "Sudan since 2024-01-01",
                            {"country": "Sudan", "date": {"$gte": "2024-01-01"}})
        assert rel.call_args.args[2] == s.TOP_K_RETRIEVAL
        assert "decay_factor" not in rec.call_args.kwargs

    def test_boost_on_surfaces_recent_doc_into_topk(self):
        """Behavioral: a recent doc ranked LOW by relevance rises into the final
        top-k via the REAL recency blend (rerank_by_recency not mocked).

        Relies on RERANK_BY_DATE=True (the project default). rerank_by_relevance
        is patched to identity so input order encodes the relevance ranking; only
        candidate index 7 is recent, the rest are ~2.5 years old."""
        import anyio
        from unittest.mock import patch, MagicMock, AsyncMock
        from datetime import datetime, timedelta
        import api.routes.chat as chat
        from config import get_settings
        s = get_settings()
        today = datetime.now()
        old = (today - timedelta(days=900)).strftime("%Y-%m-%d")
        fresh = (today - timedelta(days=5)).strftime("%Y-%m-%d")
        cands = []
        for i in range(8):
            d = MagicMock(page_content=str(i))
            d.metadata = {"date": fresh if i == 7 else old, "title": f"D{i}"}
            cands.append(d)
        retriever = MagicMock()
        retriever.ainvoke = AsyncMock(return_value=cands)
        with patch("api.routes.chat.build_retriever", return_value=retriever), \
             patch("api.routes.chat.apply_date_filter", side_effect=lambda docs, df: docs), \
             patch("api.routes.chat.dedupe_by_document", side_effect=lambda docs: docs), \
             patch("api.routes.chat.rerank_by_relevance", side_effect=lambda q, docs, n: docs[:n]), \
             patch("api.routes.chat.should_boost_recency", return_value=True):
            out = anyio.run(chat._retrieve_docs, "current situation in Sudan", {"country": "Sudan"})
        titles = [d.metadata["title"] for d in out]
        assert "D7" in titles, "the recent doc (relevance-rank 7) should rise into the final top-k"
        assert len(out) == s.TOP_K_RETRIEVAL


class TestRateLimit:
    def test_limit_exceeded_returns_429(self):
        from api.routes.chat import limiter
        limiter.enabled = True
        limiter.reset()
        try:
            with patch("api.routes.chat.get_settings",
                       return_value=MagicMock(RATE_LIMIT="1/minute")):
                from api.main import app
                from fastapi.testclient import TestClient
                client = TestClient(app)
                first = client.post("/chat", json={"message": "merhaba"})
                second = client.post("/chat", json={"message": "merhaba"})
                assert first.status_code == 200
                assert second.status_code == 429
        finally:
            limiter.reset()
            limiter.enabled = False


class TestNonStreamChatResilience:
    """İK1-1b: non-stream /chat — bounded retry on transient 503 + narrow except.

    The streaming route already rides out a transient Gemini 503 ('high demand')
    via _astream_with_retry; the non-stream /chat had no app-level retry and a broad
    except→503 that masked genuine bugs. These lock in: transient 503 is retried,
    a persistent 503 surfaces a clear busy message, and an unexpected error is a
    non-retried 500 (so real bugs aren't hidden as transient)."""

    def _retriever_with_doc(self):
        mock_doc = MagicMock()
        mock_doc.page_content = "Test"
        mock_doc.metadata = {"title": "T", "url": "http://x", "date": "2026-05-01"}
        mock_retriever = MagicMock()
        mock_retriever.ainvoke = AsyncMock(return_value=[mock_doc])
        return mock_retriever

    def test_transient_503_is_retried_then_succeeds(self):
        with patch("api.routes.chat.build_chain") as mock_chain_builder, \
             patch("api.routes.chat.build_retriever") as mock_retriever_builder, \
             patch("api.routes.chat.extract_filters", return_value={}), \
             patch("asyncio.sleep", new=AsyncMock()):
            mock_retriever_builder.return_value = self._retriever_with_doc()
            mock_chain = MagicMock()
            mock_chain.ainvoke = AsyncMock(side_effect=[
                Exception("Error code: 503 - high demand UNAVAILABLE"),
                "Recovered answer",
            ])
            mock_chain_builder.return_value = mock_chain

            from api.main import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            response = client.post("/chat", json={"message": "Syria situation", "session_id": "retry-ok"})
            assert response.status_code == 200
            assert response.json()["answer"] == "Recovered answer"
            assert mock_chain.ainvoke.call_count == 2  # one failure + one success

    def test_persistent_503_returns_503_busy_message(self):
        with patch("api.routes.chat.build_chain") as mock_chain_builder, \
             patch("api.routes.chat.build_retriever") as mock_retriever_builder, \
             patch("api.routes.chat.extract_filters", return_value={}), \
             patch("asyncio.sleep", new=AsyncMock()):
            mock_retriever_builder.return_value = self._retriever_with_doc()
            mock_chain = MagicMock()
            mock_chain.ainvoke = AsyncMock(side_effect=Exception("Error code: 503 - high demand"))
            mock_chain_builder.return_value = mock_chain

            from api.main import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            response = client.post("/chat", json={"message": "Syria", "session_id": "retry-busy"})
            assert response.status_code == 503
            detail = response.json()["detail"].lower()
            assert "busy" in detail or "high demand" in detail

    def test_unexpected_error_returns_500_and_is_not_retried(self):
        with patch("api.routes.chat.build_chain") as mock_chain_builder, \
             patch("api.routes.chat.build_retriever") as mock_retriever_builder, \
             patch("api.routes.chat.extract_filters", return_value={}), \
             patch("asyncio.sleep", new=AsyncMock()):
            mock_retriever_builder.return_value = self._retriever_with_doc()
            mock_chain = MagicMock()
            mock_chain.ainvoke = AsyncMock(side_effect=RuntimeError("boom in chain"))
            mock_chain_builder.return_value = mock_chain

            from api.main import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            response = client.post("/chat", json={"message": "Syria", "session_id": "err-500"})
            assert response.status_code == 500
            assert mock_chain.ainvoke.call_count == 1  # a genuine bug must NOT be retried

    def test_is_high_demand_helper(self):
        from api.routes.chat import _is_high_demand
        assert _is_high_demand(Exception("Error code: 503 - high demand"))
        assert _is_high_demand(Exception("status UNAVAILABLE"))
        assert _is_high_demand(Exception("the model is experiencing High Demand"))
        assert not _is_high_demand(RuntimeError("null pointer"))
        assert not _is_high_demand(ValueError("bad input"))


class TestContextDateLabel:
    def _doc(self, **meta):
        from unittest.mock import MagicMock
        d = MagicMock()
        d.page_content = "Body text"
        d.metadata = meta
        return d

    def test_context_includes_date_label(self):
        from api.routes.chat import _build_context_and_sources
        doc = self._doc(title="T", url="https://x/1", date="2026-05-01")
        context, _ = _build_context_and_sources([doc])
        assert "[1]" in context
        assert "(2026-05-01)" in context

    def test_context_missing_date_is_graceful(self):
        from api.routes.chat import _build_context_and_sources
        doc = self._doc(title="T", url="https://x/1")  # date yok
        context, _ = _build_context_and_sources([doc])
        assert "[1]" in context
        assert "tarih yok" in context

    def test_context_empty_date_is_graceful(self):
        from api.routes.chat import _build_context_and_sources
        doc = self._doc(title="T", url="https://x/1", date="")  # boş tarih
        context, _ = _build_context_and_sources([doc])
        assert "tarih yok" in context
