from unittest.mock import MagicMock, patch
import pytest
from analytics.hapi_client import fetch_rows, HapiError


def _resp(status, payload=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload or {"data": []}
    return r


@patch("analytics.hapi_client.requests.get")
def test_fetch_single_page(mock_get):
    mock_get.return_value = _resp(200, {"data": [{"population": 10}, {"population": 20}]})
    rows = fetch_rows("affected-people/idps", "AFG")
    assert len(rows) == 2
    # location_code ve app_identifier query'de mi?
    _, kwargs = mock_get.call_args
    params = kwargs["params"]
    assert params["location_code"] == "AFG"
    assert "app_identifier" in params
    assert params["output_format"] == "json"


@patch("analytics.hapi_client.requests.get")
def test_pagination_follows_until_short_page(mock_get):
    full = [{"population": i} for i in range(1000)]
    mock_get.side_effect = [
        _resp(200, {"data": full}),           # tam sayfa → devam
        _resp(200, {"data": [{"population": 1}]}),  # kısa sayfa → dur
    ]
    rows = fetch_rows("affected-people/idps", "AFG")
    assert len(rows) == 1001
    assert mock_get.call_count == 2
    # ikinci istek offset ilerledi mi?
    assert mock_get.call_args_list[1].kwargs["params"]["offset"] == 1000


@patch("analytics.hapi_client.time.sleep", lambda *_: None)
@patch("analytics.hapi_client.requests.get")
def test_retries_on_429_then_succeeds(mock_get):
    mock_get.side_effect = [_resp(429), _resp(200, {"data": [{"population": 5}]})]
    rows = fetch_rows("affected-people/idps", "AFG")
    assert len(rows) == 1
    assert mock_get.call_count == 2


@patch("analytics.hapi_client.requests.get")
def test_4xx_raises_without_retry(mock_get):
    mock_get.return_value = _resp(422)
    with pytest.raises(HapiError):
        fetch_rows("affected-people/idps", "AFG")
    assert mock_get.call_count == 1
