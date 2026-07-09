"""Central logging config + opt-in Sentry init."""
import logging
import sys
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app
from api.observability import (
    RequestIdLogFilter, configure_logging, init_sentry, request_id_var,
)


class TestConfigureLogging:
    def test_sets_root_level(self):
        configure_logging("WARNING")
        assert logging.getLogger().level == logging.WARNING
        # Restore a sane default for the rest of the suite.
        configure_logging("INFO")

    def test_level_is_case_insensitive(self):
        configure_logging("debug")
        assert logging.getLogger().level == logging.DEBUG
        configure_logging("INFO")


class TestInitSentry:
    def test_noop_without_dsn(self):
        assert init_sentry("") is False

    def test_initialises_with_dsn(self):
        fake_sdk = MagicMock()
        with patch.dict(sys.modules, {"sentry_sdk": fake_sdk}):
            ok = init_sentry("https://example@sentry.io/1", environment="production", traces_sample_rate=0.1)
        assert ok is True
        fake_sdk.init.assert_called_once()
        kwargs = fake_sdk.init.call_args.kwargs
        assert kwargs["dsn"] == "https://example@sentry.io/1"
        assert kwargs["environment"] == "production"
        assert kwargs["traces_sample_rate"] == 0.1

    def test_noop_when_sdk_missing(self):
        # DSN set but the SDK cannot be imported → graceful no-op, never raises.
        with patch.dict(sys.modules, {"sentry_sdk": None}):
            assert init_sentry("https://example@sentry.io/1") is False


class TestRequestId:
    """P16-01 — correlation id on every request/response and in log records."""

    def test_response_carries_request_id_header(self):
        r = TestClient(app).get("/health")
        assert r.headers.get("X-Request-ID"), "every response should carry a correlation id"

    def test_inbound_request_id_is_reused(self):
        r = TestClient(app).get("/health", headers={"X-Request-ID": "trace-abc-123"})
        assert r.headers.get("X-Request-ID") == "trace-abc-123"

    def test_filter_injects_current_value(self):
        rec = logging.LogRecord("n", logging.INFO, "p", 1, "msg", None, None)
        token = request_id_var.set("abc123")
        try:
            assert RequestIdLogFilter().filter(rec) is True
            assert rec.request_id == "abc123"
        finally:
            request_id_var.reset(token)


class TestSecurityAuditLog:
    """P16-03 — security-relevant events leave an audit record."""

    def test_failed_login_is_audit_logged(self, caplog):
        with caplog.at_level(logging.WARNING, logger="api.routes.auth"):
            TestClient(app).post(
                "/auth/login",
                json={"email": "nobody@example.com", "password": "whatever123"},
            )
        assert any("login failed" in r.getMessage().lower() for r in caplog.records), \
            "a failed login must leave a WARNING audit record"
