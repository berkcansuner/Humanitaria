"""Chat prompt rule 5 asks the model to state an applied date or country filter at
the start of its answer; the filters extracted from the question are therefore
stated to the model in the prompt (it could not know them otherwise)."""
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from rag.chain import describe_filters


def test_no_filters_reads_none():
    assert describe_filters({}) == "none"
    assert describe_filters(None) == "none"


def test_filters_are_spelled_out():
    text = describe_filters({
        "country": "Sudan", "theme": "Health", "date": {"$gte": "2026-01-01"},
    })
    assert text == "country: Sudan; topic: Health; documents dated from 2026-01-01"


def test_closed_date_range():
    text = describe_filters({"date": {"$gte": "2026-01-01", "$lte": "2026-06-30"}})
    assert text == "documents dated from 2026-01-01 to 2026-06-30"


def _post(path, filters):
    captured = {}

    async def fake_astream(payload, *a, **k):
        captured.update(payload)
        yield "ok"

    async def fake_ainvoke(payload, *a, **k):
        captured.update(payload)
        return "ok"

    # Dated inside the filter's range, so the date filter keeps it.
    doc = MagicMock(page_content="text", metadata={"title": "T", "url": "http://x", "date": "2026-05-01"})
    retriever = MagicMock(ainvoke=AsyncMock(return_value=[doc]))
    chain = MagicMock(astream=fake_astream, ainvoke=fake_ainvoke)
    with patch("api.routes.chat.build_chain", return_value=chain), \
         patch("api.routes.chat.build_retriever", return_value=retriever), \
         patch("api.routes.chat.extract_filters", return_value=filters):
        from api.main import app
        r = TestClient(app).post(path, json={"message": "Sudan health situation since January 2026"})
    assert r.status_code == 200
    return captured


def test_chat_routes_pass_applied_filters_to_chain():
    filters = {"country": "Sudan", "date": {"$gte": "2026-01-01"}}
    for path in ("/chat/stream", "/chat"):
        captured = _post(path, filters)
        assert captured.get("applied_filters") == describe_filters(filters), path


def test_prompt_states_the_applied_filters():
    from rag import chain as chain_mod
    s = MagicMock(GEMINI_API_KEY="k", GEMINI_BASE_URL="https://x/openai/", GEMINI_LLM_MODEL="m",
                  GEMINI_REASONING_EFFORT="", CHAT_LLM_TIMEOUT=45)
    with patch.object(chain_mod, "get_settings", return_value=s):
        chain_mod._chain = None
        prompt = chain_mod.build_chain().first
        chain_mod._chain = None
    msgs = prompt.format_messages(context="", chat_history=[], question="q",
                                  applied_filters="country: Sudan")
    assert "Filters applied to the document search: country: Sudan." in msgs[0].content
    # Callers that don't pass applied_filters still format (no filters).
    msgs = prompt.format_messages(context="", chat_history=[], question="q")
    assert "Filters applied to the document search: none." in msgs[0].content
