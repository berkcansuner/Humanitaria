"""Central logging config + opt-in Sentry init."""
import logging
import sys
from unittest.mock import MagicMock, patch

from api.observability import configure_logging, init_sentry


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
