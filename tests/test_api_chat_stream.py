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
                yield "Sadece ilk belgeden bilgi [1]."

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
                yield "Atıf içermeyen bir özet."

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
            "message": "Hangi ülke, zaman aralığı veya konu?",
            "suggestions": {"countries": ["Sudan"], "time_periods": ["son 1 ay"], "themes": ["Health"]},
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
            mock_retriever.ainvoke = AsyncMock(side_effect=RuntimeError("Chroma offline"))
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


class TestApiKeyAuth:
    """Optional X-API-Key auth on the chat endpoints."""

    def _settings(self, api_key):
        return MagicMock(API_KEY=api_key, RATE_LIMIT="100/minute")

    def test_missing_key_rejected_when_configured(self):
        with patch("api.routes.chat.get_settings", return_value=self._settings("secret")):
            from api.main import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            # Greeting path needs no retrieval; auth runs before the handler.
            response = client.post("/chat", json={"message": "merhaba"})
            assert response.status_code == 401

    def test_valid_key_accepted(self):
        with patch("api.routes.chat.get_settings", return_value=self._settings("secret")):
            from api.main import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            response = client.post(
                "/chat", json={"message": "merhaba"}, headers={"X-API-Key": "secret"}
            )
            assert response.status_code == 200

    def test_no_auth_when_key_empty(self):
        with patch("api.routes.chat.get_settings", return_value=self._settings("")):
            from api.main import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            response = client.post("/chat", json={"message": "merhaba"})
            assert response.status_code == 200


class TestRateLimit:
    def test_limit_exceeded_returns_429(self):
        from api.routes.chat import limiter
        limiter.enabled = True
        limiter.reset()
        try:
            with patch("api.routes.chat.get_settings",
                       return_value=MagicMock(API_KEY="", RATE_LIMIT="1/minute")):
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
