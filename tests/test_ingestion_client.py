import pytest
from unittest.mock import patch, MagicMock
from ingestion.client import ReliefWebClient, ENDPOINT_CONFIG
from config import get_settings


class TestReliefWebClient:
    def test_init_uses_config(self):
        get_settings.cache_clear()
        with patch.dict(
            "os.environ",
            {"RELIEFWEB_BASE_URL": "https://api.reliefweb.int/v2"},
            clear=False,
        ):
            client = ReliefWebClient()
        assert client.base_url == "https://api.reliefweb.int/v2"
        # ReliefWeb uses appname query param — no Authorization header
        assert "Authorization" not in client.headers
        assert client.headers["Content-Type"] == "application/json"

    def test_fetch_reports_pagination(self):
        client = ReliefWebClient()
        mock_data = {
            "data": [
                {"id": "1", "fields": {"title": "Test Report", "body": "Body", "date": {"created": "2026-04-01"}}}
            ],
            "totalCount": 1
        }
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_data
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            reports = client.fetch_reports(limit=1)
            assert len(reports) == 1
            assert reports[0]["id"] == "1"

    def test_fetch_reports_429_backoff(self):
        client = ReliefWebClient()
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.raise_for_status.side_effect = Exception("429")
            mock_post.return_value = mock_response
            with patch("time.sleep") as mock_sleep:
                with pytest.raises(Exception):
                    client.fetch_reports(limit=1)
                assert mock_sleep.call_count >= 2

    def test_fetch_generic_endpoint(self):
        client = ReliefWebClient()
        mock_data = {"data": [{"id": "1", "fields": {"name": "Test Disaster"}}], "totalCount": 1}
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_data
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            result = client.fetch("disasters", limit=1)
            assert len(result) == 1
            call_args = mock_post.call_args
            assert "/disasters" in call_args[0][0]

    def test_fetch_unknown_endpoint_raises(self):
        client = ReliefWebClient()
        with pytest.raises(ValueError, match="Unknown endpoint"):
            client.fetch("nonexistent")

    def test_fetch_reports_delegates_to_fetch(self):
        client = ReliefWebClient()
        mock_data = {"data": [{"id": "1"}], "totalCount": 1}
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_data
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            client.fetch_reports(limit=1)
            call_url = mock_post.call_args[0][0]
            assert call_url.endswith("/reports")

    def test_fetch_with_country_filter(self):
        client = ReliefWebClient()
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"data": []}
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            client.fetch("reports", limit=1, country="SDN")
            payload = mock_post.call_args[1]["json"]
            assert payload["filter"] == {"field": "primary_country.iso3", "value": "SDN"}

    def test_fetch_with_country_and_date_filter(self):
        client = ReliefWebClient()
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"data": []}
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            client.fetch("reports", limit=1, country="SDN", date_from="2026-01-01")
            payload = mock_post.call_args[1]["json"]
            assert payload["filter"]["operator"] == "AND"
            fields = {c["field"] for c in payload["filter"]["conditions"]}
            assert fields == {"date.created", "primary_country.iso3"}

    def test_endpoint_config_has_all_endpoints(self):
        assert "reports" in ENDPOINT_CONFIG
        assert "disasters" in ENDPOINT_CONFIG
        assert "countries" in ENDPOINT_CONFIG