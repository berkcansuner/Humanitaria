import pytest
from unittest.mock import patch
from config import Settings, get_settings


class TestConfig:
    def test_settings_loads_env(self):
        with patch.dict("os.environ", {"CHUNK_SIZE": "500", "TOP_K_RETRIEVAL": "3"}, clear=False):
            s = Settings()
            assert s.CHUNK_SIZE == 500
            assert s.TOP_K_RETRIEVAL == 3

    def test_get_settings_cached(self):
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
