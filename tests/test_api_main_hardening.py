"""Production-hardening helpers in api.main: /docs gating + config fail-fast."""
import pytest

from config import Settings, DEFAULT_SESSION_SECRET
from api.main import _docs_kwargs, _verify_production_config


class TestDocsGating:
    def test_docs_disabled_in_production(self):
        s = Settings(_env_file=None, ENVIRONMENT="production")
        assert _docs_kwargs(s) == {"docs_url": None, "redoc_url": None, "openapi_url": None}

    def test_docs_enabled_in_dev(self):
        s = Settings(_env_file=None)
        assert _docs_kwargs(s) == {}


class TestSessionSecretFailFast:
    def test_raises_on_default_secret_in_production(self):
        s = Settings(_env_file=None, ENVIRONMENT="production")  # keeps default secret
        with pytest.raises(RuntimeError, match="AUTH_SESSION_SECRET"):
            _verify_production_config(s)

    def test_ok_with_custom_secret_in_production(self):
        s = Settings(
            _env_file=None,
            ENVIRONMENT="production",
            AUTH_SESSION_SECRET="a-strong-random-secret-value",
        )
        _verify_production_config(s)  # must not raise

    def test_ok_in_dev_with_default_secret(self):
        s = Settings(_env_file=None)  # dev + default secret is fine
        assert s.AUTH_SESSION_SECRET == DEFAULT_SESSION_SECRET
        _verify_production_config(s)  # must not raise
