"""Per-user storage bounds (security audit run-1): conversation/report counts
are capped, conversation writes are rate-limited, and a create/rename returns
one row instead of re-reading the user's whole list."""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.limiter import limiter
from api.main import app
from rag import conversations as convo_store
from rag import reports as report_store


def _settings(**kw):
    s = MagicMock(RATE_LIMIT="1000/minute", MAX_CONVERSATIONS_PER_USER=2, MAX_REPORTS_PER_USER=1)
    for k, v in kw.items():
        setattr(s, k, v)
    return s


def test_conversation_create_capped(test_user_id):
    client = TestClient(app)
    with patch("api.routes.conversations.get_settings", return_value=_settings()):
        assert client.post("/conversations", json={}).status_code == 200
        assert client.post("/conversations", json={}).status_code == 200
        assert client.post("/conversations", json={}).status_code == 409


def test_conversation_create_and_rename_do_not_list_everything():
    client = TestClient(app)
    with patch("api.routes.conversations.get_settings", return_value=_settings()), \
         patch("api.routes.conversations.store.list_conversations",
               side_effect=AssertionError("full list read")):
        r = client.post("/conversations", json={"title": "A"})
        assert r.status_code == 200 and r.json()["title"] == "A"
        r2 = client.patch(f"/conversations/{r.json()['id']}", json={"title": "B"})
        assert r2.status_code == 200 and r2.json()["title"] == "B"


def test_conversation_writes_are_rate_limited():
    client = TestClient(app)
    limiter.enabled = True
    limiter.reset()
    try:
        with patch("api.routes.conversations.get_settings", return_value=_settings(RATE_LIMIT="1/minute")):
            assert client.post("/conversations", json={}).status_code == 200
            assert client.post("/conversations", json={}).status_code == 429
    finally:
        limiter.reset()
        limiter.enabled = False


def test_chat_cannot_open_conversations_past_the_cap(test_user_id):
    convo_store.create_conversation(test_user_id, "c1", "x")
    convo_store.create_conversation(test_user_id, "c2", "x")
    with patch("api.routes.conversations.get_settings", return_value=_settings()):
        r = TestClient(app).post("/chat", json={"message": "hello there friend"})
    assert r.status_code == 409


def test_report_generation_capped(test_user_id):
    report_store.create_report("r1", test_user_id, country="Sudan", theme=None, date_from=None,
                               date_to=None, language="en", title="t", content="c",
                               sources=None, doc_count=0)
    with patch("api.routes.reports.get_settings", return_value=_settings()):
        r = TestClient(app).post("/reports/stream", json={"country": "Sudan"})
    assert r.status_code == 409
