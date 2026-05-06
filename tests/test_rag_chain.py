import pytest
from unittest.mock import patch, MagicMock
from rag.retriever import build_retriever
from rag.memory import build_memory
from rag.chain import build_chain


class TestRetrieverAndMemory:
    def test_build_retriever_returns_callable(self):
        with patch("rag.retriever.chromadb.PersistentClient") as MockClient:
            mock_collection = MagicMock()
            mock_collection.query.return_value = {
                "ids": [["id1"]], "documents": [["doc1"]], "metadatas": [[{"url": "u1"}]], "distances": [[0.1]]
            }
            mock_client = MagicMock()
            mock_client.get_collection.return_value = mock_collection
            MockClient.return_value = mock_client
            retriever = build_retriever(filter={"country": "Iran"})
            docs = retriever.invoke("test query")
            assert len(docs) == 1
            assert docs[0].page_content == "doc1"

    def test_build_memory(self):
        mem = build_memory()
        assert mem is not None
        assert mem.k == 5


class TestChain:
    def test_build_chain(self):
        with patch("rag.chain.ChatOllama") as MockLLM, \
             patch("rag.chain.build_retriever") as mock_retriever_builder:
            mock_llm = MagicMock()
            MockLLM.return_value = mock_llm
            mock_retriever = MagicMock()
            mock_retriever_builder.return_value = mock_retriever
            chain = build_chain(filter={"country": "Iran"})
            assert chain is not None
