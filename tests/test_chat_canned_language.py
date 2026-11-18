"""The fixed greeting and the 'no documents found' reply follow the language of the
user's question, like the LLM answers do (no LLM call is involved in either)."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.routes import chat as chat_mod

EN_GREETING = "Hello! How can I help you with humanitarian reports?"
TR_GREETING = "Merhaba! İnsani yardım raporlarıyla ilgili nasıl yardımcı olabilirim?"
TR_QUESTION = "Sudan'daki gıda güvensizliği durumu nedir?"


def _client():
    from api.main import app
    return TestClient(app)


def _empty_retrieval():
    retriever = MagicMock(ainvoke=AsyncMock(return_value=[]))
    return (
        patch("api.routes.chat.build_retriever", return_value=retriever),
        patch("api.routes.chat.extract_filters", return_value={"country": "Sudan"}),
    )


def _sse_tokens(text: str) -> str:
    out, event = "", None
    for line in text.splitlines():
        if line.startswith("event:"):
            event = line.split(":", 1)[1].strip()
        elif line.startswith("data:") and event == "token":
            out += json.loads(line.split(":", 1)[1])["content"]
    return out


@pytest.mark.parametrize("word", ["merhaba", "Selam!", "nasılsın?", "günaydın", "iyi günler"])
def test_turkish_greeting_gets_turkish_reply(word):
    r = _client().post("/chat", json={"message": word})
    assert r.json()["answer"] == TR_GREETING


@pytest.mark.parametrize("word", ["hello", "Hi!", "good morning", "how are you"])
def test_english_greeting_gets_english_reply(word):
    r = _client().post("/chat", json={"message": word})
    assert r.json()["answer"] == EN_GREETING


def test_streaming_greeting_follows_language():
    tr = _client().post("/chat/stream", json={"message": "merhaba"})
    assert _sse_tokens(tr.text) == TR_GREETING
    en = _client().post("/chat/stream", json={"message": "hello"})
    assert _sse_tokens(en.text) == EN_GREETING


def test_turkish_question_without_documents_gets_turkish_message():
    p1, p2 = _empty_retrieval()
    with p1, p2:
        r = _client().post("/chat", json={"message": TR_QUESTION})
    answer = r.json()["answer"]
    assert answer.startswith("Veritabanımızda **Sudan** için eşleşen belge bulunamadı.")
    assert "yeniden yazabilirsiniz" in answer


def test_english_question_without_documents_stays_english():
    p1, p2 = _empty_retrieval()
    with p1, p2:
        r = _client().post("/chat", json={"message": "What is the food security situation in Sudan?"})
    assert r.json()["answer"].startswith("No matching documents were found in our database for **Sudan**.")


def test_streaming_no_documents_follows_language():
    p1, p2 = _empty_retrieval()
    with p1, p2:
        r = _client().post("/chat/stream", json={"message": TR_QUESTION})
    assert "**Sudan** için eşleşen belge bulunamadı" in _sse_tokens(r.text)


def test_no_docs_message_variants():
    filters = {"country": ["Sudan", "Chad"], "theme": "Health", "date": {"$gte": "2025-01-01"}}
    tr = chat_mod.no_docs_message(filters, "tr")
    assert "**Sudan** + **Chad** + **Health** + belirtilen tarih aralığı için" in tr
    assert chat_mod.no_docs_message({}, "tr").startswith("Veritabanımızda bu sorgu için")
    # Unknown languages fall back to English.
    assert chat_mod.no_docs_message(filters, "fr") == chat_mod.no_docs_message(filters, "en")
    assert chat_mod.greeting_reply("fr") == EN_GREETING
