import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestChainlitApp:
    @pytest.mark.asyncio
    async def test_on_message_calls_chain(self):
        with patch("chainlit_app.build_chain") as mock_build_chain, \
             patch("chainlit_app.extract_filters") as mock_extract:
            mock_chain = MagicMock()
            mock_chain.return_value = {"answer": "Test answer", "source_documents": []}
            mock_build_chain.return_value = mock_chain
            mock_extract.return_value = {}
            from chainlit_app import on_message
            msg = MagicMock()
            msg.content = "test"
            with patch("chainlit.Message") as MockMsg:
                await on_message(msg)
                mock_chain.assert_called_once()
