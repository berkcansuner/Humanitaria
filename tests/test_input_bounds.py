"""Input size/shape bounds (security audit run-1: request-body, session_id,
report fields)."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.real_auth
def test_oversized_body_rejected_before_json_decode(client):
    big = b'{"message": "' + b"a" * (200 * 1024) + b'"}'
    with patch("json.loads", side_effect=AssertionError("body was decoded")):
        r = client.post("/chat", content=big, headers={"Content-Type": "application/json"})
    assert r.status_code == 413


def test_oversized_chunked_body_rejected(client):
    def chunks():
        for _ in range(40):
            yield b"x" * 8192
    r = client.post("/chat", content=chunks(), headers={"Content-Type": "application/json"})
    assert r.status_code == 413


def test_normal_body_still_accepted(client):
    # A 4000-char message (the model maximum) must pass the size gate; the request
    # may still fail later for unrelated reasons, just never with 413.
    with patch("api.routes.chat._plan_retrieval", side_effect=RuntimeError("stop")):
        r = client.post("/chat", json={"message": "a" * 4000})
    assert r.status_code != 413


def test_overlong_session_id_rejected(client):
    from rag import history
    r = client.post("/chat", json={"message": "hi there", "session_id": "s" * 5000})
    assert r.status_code == 422
    assert "s" * 5000 not in history._session_histories


def test_session_id_charset_enforced(client):
    r = client.post("/chat", json={"message": "hi there", "session_id": "bad id/../x"})
    assert r.status_code == 422


def test_report_theme_must_be_known(client):
    r = client.post("/reports/stream", json={"country": "Sudan", "theme": "x" * 10000,
                                             "report_type": "situation"})
    assert r.status_code == 422


def test_report_dates_must_be_iso(client):
    r = client.post("/reports/stream", json={"country": "Sudan", "date_from": "not-a-date"})
    assert r.status_code == 422


def test_report_valid_fields_pass_validation(client):
    with patch("api.routes.reports.retrieve_for_report", side_effect=RuntimeError("stop")):
        r = client.post("/reports/stream", json={"country": "Sudan", "theme": "Health",
                                                 "date_from": "2026-01-01", "date_to": "2026-06-30"})
    assert r.status_code == 200
