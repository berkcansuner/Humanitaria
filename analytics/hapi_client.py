"""HDX HAPI (Humanitarian API) istemcisi.

Bir endpoint'ten bir ülkenin tüm satırlarını sayfalama tamamlanana dek çeker.
429/5xx geçici hatalarda sınırlı backoff ile yeniden dener; 4xx'te hemen HapiError
fırlatır (retry yok — ingestion/client.py ile aynı disiplin). Ağ dışı bir durum
tutmaz; app_identifier config'den okunur (boşsa daha düşük rate limit ile çalışır).
"""
import logging
import time

import requests

from config import get_settings

logger = logging.getLogger(__name__)

_PAGE_LIMIT = 1000
_MAX_RETRIES = 3
_BACKOFF_BASE = 1.5


class HapiError(Exception):
    """HAPI'den kurtarılamaz hata (4xx veya retry'lar tükendi)."""


def fetch_rows(endpoint: str, iso3: str, extra_params: dict | None = None,
               admin_level: int | None = None) -> list[dict]:
    settings = get_settings()
    base = settings.HDX_HAPI_BASE_URL.rstrip("/")
    url = f"{base}/{endpoint}"
    lvl = admin_level if admin_level is not None else settings.HDX_HAPI_ADMIN_LEVEL
    params = {
        "output_format": "json",
        "location_code": iso3,
        "admin_level": lvl,
        "limit": _PAGE_LIMIT,
        "offset": 0,
    }
    params["app_identifier"] = settings.HDX_APP_IDENTIFIER or ""
    if extra_params:
        params.update(extra_params)

    rows: list[dict] = []
    while True:
        page = _get_page(url, dict(params), settings.HDX_HAPI_TIMEOUT)
        rows.extend(page)
        if len(page) < _PAGE_LIMIT:
            break
        params["offset"] += _PAGE_LIMIT
    logger.info("HAPI %s %s -> %d satir", endpoint, iso3, len(rows))
    return rows


def _get_page(url: str, params: dict, timeout: int) -> list[dict]:
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        resp = requests.get(url, params=params, timeout=timeout)
        code = resp.status_code
        if code == 200:
            return resp.json().get("data", [])
        if code == 429 or 500 <= code < 600:
            wait = _BACKOFF_BASE ** attempt
            logger.warning("HAPI %s → HTTP %d, %.1fs sonra retry (%d/%d)",
                           url, code, wait, attempt + 1, _MAX_RETRIES)
            last_exc = HapiError(f"HAPI {code}")
            time.sleep(wait)
            continue
        raise HapiError(f"HAPI {code} for {url}")   # 4xx → retry yok
    raise HapiError(f"HAPI retries exhausted for {url}") from last_exc
