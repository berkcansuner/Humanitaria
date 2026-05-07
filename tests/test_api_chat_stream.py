import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.fixture(autouse=True)
def _import_api():
    import api.routes.chat  # noqa: F401 — ensure module is loaded for patching


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