import pytest
from unittest.mock import patch, MagicMock
from ingestion.client import ReliefWebClient


class TestReliefWebClient:
    def test_init_uses_config(self):
        client = ReliefWebClient()
        assert client.base_url == "https://api.reliefweb.int/v1"
        assert "Authorization" in client.headers or "appname" in client.headers

    def test_fetch_reports_pagination(self):
        client = ReliefWebClient()
        mock_data = {
            "data": [
                {"id": "1", "fields": {"title": "Test Report", "body": "Body", "date": {"created": "2026-04-01"}}}
            ],
            "totalCount": 1
        }
        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_data
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            reports = client.fetch_reports(limit=1)
            assert len(reports) == 1
            assert reports[0]["id"] == "1"

    def test_fetch_reports_429_backoff(self):
        client = ReliefWebClient()
        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.raise_for_status.side_effect = Exception("429")
            mock_get.return_value = mock_response
            with patch("time.sleep") as mock_sleep:
                with pytest.raises(Exception):
                    client.fetch_reports(limit=1)
                assert mock_sleep.call_count >= 2
