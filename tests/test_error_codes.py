"""Machine error codes sit next to the unchanged `detail` in API error bodies."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app

SIGNUP = {"email": "alice@example.com", "password": "password123", "name": "Alice"}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.real_auth
def test_wrong_password_has_invalid_credentials_code(client):
    client.post("/auth/signup", json=SIGNUP)
    r = client.post("/auth/login", json={"email": SIGNUP["email"], "password": "wrong-pass-1"})
    assert r.status_code == 401
    assert r.json() == {"detail": "Invalid email or password", "code": "invalid_credentials"}


@pytest.mark.real_auth
def test_duplicate_signup_has_email_taken_code(client):
    client.post("/auth/signup", json=SIGNUP)
    r = client.post("/auth/signup", json=SIGNUP)
    assert r.status_code == 409
    assert r.json() == {"detail": "Email already registered", "code": "email_taken"}


@pytest.mark.real_auth
def test_unauthenticated_has_not_authenticated_code(client):
    r = client.patch("/auth/me", json={"name": "x"})
    assert r.status_code == 401
    assert r.json() == {"detail": "Not authenticated", "code": "not_authenticated"}


@pytest.mark.real_auth
def test_short_password_signup_has_weak_password_code(client):
    r = client.post("/auth/signup", json={**SIGNUP, "password": "short"})
    assert r.status_code == 422
    assert r.json()["code"] == "weak_password"


def test_empty_chat_message_has_message_empty_code(client):
    r = client.post("/chat", json={"message": ""})
    assert r.status_code == 422
    assert r.json()["code"] == "message_empty"
    assert isinstance(r.json()["detail"], list)


def test_blank_chat_message_has_message_empty_code(client):
    r = client.post("/chat/stream", json={"message": "   "})
    assert r.status_code == 422
    assert r.json()["code"] == "message_empty"


def test_long_chat_message_has_message_too_long_code(client):
    r = client.post("/chat", json={"message": "a" * 4001})
    assert r.status_code == 422
    assert r.json()["code"] == "message_too_long"


def test_other_validation_error_keeps_detail_list_and_adds_code(client):
    r = client.post("/chat", json={})
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "validation_failed"
    assert body["detail"][0]["type"] == "missing"


def test_missing_report_has_not_found_code(client):
    r = client.get("/reports/does-not-exist")
    assert r.status_code == 404
    assert r.json() == {"detail": "Report not found", "code": "not_found"}


def test_missing_conversation_has_not_found_code(client):
    r = client.get("/conversations/nope/messages")
    assert r.status_code == 404
    assert r.json() == {"detail": "Conversation not found", "code": "not_found"}


@pytest.mark.real_auth
def test_oversized_body_has_body_too_large_code(client):
    big = b'{"message": "' + b"a" * (200 * 1024) + b'"}'
    r = client.post("/chat", content=big, headers={"Content-Type": "application/json"})
    assert r.status_code == 413
    assert r.json() == {"detail": "Request body too large", "code": "body_too_large"}


def test_chunked_oversized_body_has_body_too_large_code(client):
    def chunks():
        for _ in range(100):
            yield b"a" * 1024

    r = client.post("/chat", content=chunks(), headers={"Content-Type": "application/json"})
    assert r.status_code == 413
    assert r.json()["code"] == "body_too_large"


def test_rate_limited_has_code_and_keeps_error(client):
    from api.routes.chat import limiter

    limiter.enabled = True
    limiter.reset()
    try:
        with patch("api.routes.chat.get_settings", return_value=MagicMock(RATE_LIMIT="1/minute")):
            client.post("/chat", json={"message": "merhaba"})
            second = client.post("/chat", json={"message": "merhaba"})
        assert second.status_code == 429
        body = second.json()
        assert body["code"] == "rate_limited"
        assert "error" in body
    finally:
        limiter.reset()
        limiter.enabled = False


def _chat_with_retriever_error(client, path, exc):
    with patch("api.routes.chat.build_retriever") as builder, \
         patch("api.routes.chat.extract_filters", return_value={}):
        retriever = MagicMock()
        retriever.ainvoke = AsyncMock(side_effect=exc)
        builder.return_value = retriever
        return client.post(path, json={"message": "Sudan situation"})


def _error_event(text):
    import json
    lines = text.replace("\r\n", "\n").split("\n")
    for i, line in enumerate(lines):
        if line == "event: error":
            return json.loads(lines[i + 1][len("data: "):])
    raise AssertionError("no error event")


@pytest.mark.parametrize("exc, code", [
    (RuntimeError("boom"), "chat_failed"),
    (Exception("Error code: 503 - high demand UNAVAILABLE"), "model_busy"),
    (Exception("Error code: 402 - RESOURCE_EXHAUSTED prepayment credits are depleted"), "quota_exhausted"),
])
def test_chat_stream_error_event_carries_code_and_message(client, exc, code):
    r = _chat_with_retriever_error(client, "/chat/stream", exc)
    event = _error_event(r.text)
    assert event["code"] == code
    assert event["message"]
    assert "boom" not in event["message"]


@pytest.mark.parametrize("exc, status, code", [
    (RuntimeError("boom"), 500, "chat_failed"),
    (Exception("Error code: 503 - high demand UNAVAILABLE"), 503, "model_busy"),
])
def test_chat_non_stream_error_has_code(client, exc, status, code):
    with patch("asyncio.sleep", new=AsyncMock()):
        r = _chat_with_retriever_error(client, "/chat", exc)
    assert r.status_code == status
    assert r.json()["code"] == code


def test_conversation_limit_has_code(client):
    with patch("api.routes.conversations.can_open_conversation", return_value=False):
        r = client.post("/conversations", json={"title": "x"})
    assert r.status_code == 409
    assert r.json()["code"] == "conversation_limit"


def test_report_limit_has_code(client):
    with patch("api.routes.reports.report_store.count_reports", return_value=10**6):
        r = client.post("/reports/stream", json={
            "country": "Sudan", "theme": "Health",
            "date_from": "2026-01-01", "date_to": "2026-02-01", "language": "en",
        })
    assert r.status_code == 409
    assert r.json()["code"] == "report_limit"


@pytest.mark.parametrize("exc, code", [
    (RuntimeError("boom"), "report_failed"),
    (Exception("Error code: 503 - high demand UNAVAILABLE"), "model_busy"),
])
def test_report_stream_error_event_carries_code(client, exc, code):
    with patch("api.routes.reports.technical_report.compute_findings", side_effect=exc):
        r = client.post("/reports/stream", json={
            "country": "Afghanistan", "report_type": "technical_monitoring", "language": "en",
        })
    event = _error_event(r.text)
    assert event["code"] == code
    assert "boom" not in event["message"]
