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
                yield "World"

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
            assert "".join(tokens) == "Hello World"

            # Sources should contain the mocked doc
            src_events = [e for e in events if e["event"] == "sources"]
            assert len(src_events) == 1
            sources = src_events[0]["data"]["sources"]
            assert len(sources) == 1
            assert sources[0]["title"] == "WFP Report"
            assert sources[0]["country"] == "Yemen"

            # Session event should echo the session_id
            sess_events = [e for e in events if e["event"] == "session"]
            assert len(sess_events) == 1
            assert sess_events[0]["data"]["session_id"] == "evt-test"

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
