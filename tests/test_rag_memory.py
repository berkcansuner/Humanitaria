import pytest
from langchain.memory import ConversationBufferWindowMemory
from rag.memory import build_memory


class TestMemory:
    def test_build_memory_returns_correct_type(self):
        mem = build_memory()
        assert isinstance(mem, ConversationBufferWindowMemory)

    def test_build_memory_k_is_five(self):
        mem = build_memory()
        assert mem.k == 5

    def test_build_memory_returns_messages(self):
        mem = build_memory()
        assert mem.return_messages is True

    def test_build_memory_key(self):
        mem = build_memory()
        assert mem.memory_key == "chat_history"

    def test_build_memory_output_key(self):
        mem = build_memory()
        assert mem.output_key == "answer"
