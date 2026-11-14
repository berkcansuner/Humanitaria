"""The chat answer language is decided in code and stated to the model, instead of
leaving it to the model to infer from a short question next to Context documents
in other languages (a Turkish follow-up was answered in Spanish in production)."""
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from rag.chain import DEFAULT_ANSWER_LANGUAGE, answer_language


def test_clear_single_message():
    assert answer_language("Yemen'de gıda güvensizliği durumu nedir?", []) == "Turkish"
    assert answer_language("What is the food security situation in Yemen?", []) == "English"


def test_short_ambiguous_follow_up_uses_conversation_language():
    history = [HumanMessage("Yemen'de gıda güvensizliği durumu nedir?"),
               AIMessage("Yemen'de durum ciddi [1].")]
    for follow_up in ("peki ya 2025?", "neden?", "peki kuzeyde durum ne?"):
        assert answer_language(follow_up, history) == "Turkish", follow_up


def test_clear_switch_of_language_wins_over_history():
    history = [HumanMessage("Yemen'de gıda güvensizliği durumu nedir?")]
    assert answer_language("What about the northern governorates?", history) == "English"


def test_unsupported_or_unclear_language_falls_back_to_model_rule():
    assert answer_language("Quelle est la situation alimentaire au Mali ?", []) == DEFAULT_ANSWER_LANGUAGE
    assert answer_language("2025?", []) == DEFAULT_ANSWER_LANGUAGE


def test_chat_route_passes_answer_language_to_chain():
    captured = {}

    async def fake_astream(payload, *a, **k):
        captured.update(payload)
        yield "ok"

    doc = MagicMock(page_content="Contenido en español", metadata={"title": "T", "url": "http://x"})
    retriever = MagicMock(ainvoke=AsyncMock(return_value=[doc]))
    chain = MagicMock(astream=fake_astream)
    with patch("api.routes.chat.build_chain", return_value=chain), \
         patch("api.routes.chat.build_retriever", return_value=retriever), \
         patch("api.routes.chat.extract_filters", return_value={}):
        from api.main import app
        r = TestClient(app).post("/chat/stream", json={"message": "Yemen'de gıda güvensizliği durumu nedir?"})
    assert r.status_code == 200
    assert captured.get("answer_language") == "Turkish"


def test_prompt_states_the_language_and_warns_about_context_languages():
    from rag.chain import build_chain
    from rag import chain as chain_mod
    s = MagicMock(GEMINI_API_KEY="k", GEMINI_BASE_URL="https://x/openai/", GEMINI_LLM_MODEL="gemini-2.5-flash",
                  GEMINI_REASONING_EFFORT="", CHAT_LLM_TIMEOUT=45)
    with patch.object(chain_mod, "get_settings", return_value=s):
        chain_mod._chain = None
        prompt = build_chain().first
        chain_mod._chain = None
    msgs = prompt.format_messages(context="[1] texto", chat_history=[], question="q", answer_language="Turkish")
    system = msgs[0].content
    assert "Answer in Turkish" in system
    assert "never take the answer language from" in system
    # Callers that don't pass answer_language still work (default rule).
    msgs = prompt.format_messages(context="", chat_history=[], question="q")
    assert DEFAULT_ANSWER_LANGUAGE in msgs[0].content
