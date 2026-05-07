import logging
import time
from typing import List, Dict, Any, Optional
import requests
from config import get_settings

logger = logging.getLogger(__name__)

ENDPOINT_CONFIG = {
    "reports": {
        "path": "/reports",
        "fields": [
            "title", "body", "date.created", "source.name",
            "primary_country.name", "theme.name", "format.name", "file",
        ],
        "sort": "date.created:desc",
    },
    "disasters": {
        "path": "/disasters",
        "fields": [
            "name", "description", "date.created", "primary_country.name",
            "country.name", "type.name", "primary_type.name", "status", "glide", "url",
        ],
        "sort": "date.created:desc",
    },
    "countries": {
        "path": "/countries",
        "fields": [
            "name", "description", "date.created", "iso3", "shortname", "status", "url",
        ],
        "sort": "date.created:desc",
    },
}


class ReliefWebClient:
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.RELIEFWEB_BASE_URL
        self.api_key = self.settings.RELIEFWEB_API_KEY
        self.headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    def fetch(
        self,
        endpoint: str,
        limit: int = 100,
        offset: int = 0,
        sort: Optional[str] = None,
        fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        config = ENDPOINT_CONFIG.get(endpoint)
        if config is None:
            raise ValueError(f"Unknown endpoint: {endpoint}. Must be one of: {list(ENDPOINT_CONFIG)}")

        url = f"{self.base_url}{config['path']}"
        params = {}
        if self.settings.RELIEFWEB_APPNAME:
            params["appname"] = self.settings.RELIEFWEB_APPNAME
        payload = {
            "limit": min(limit, 1000),
            "offset": offset,
            "sort": [sort or config["sort"]],
            "fields": {"include": fields or config["fields"]},
        }
        max_retries = 5
        backoff = 1.0
        for attempt in range(max_retries):
            try:
                resp = requests.post(url, headers=self.headers, params=params, json=payload, timeout=30)
                if resp.status_code == 429:
                    if attempt < max_retries - 1:
                        logger.warning("Rate limited (429), backing off %.1fs", backoff)
                        time.sleep(backoff)
                        backoff *= 2
                        continue
                    else:
                        raise requests.RequestException("Max retries exceeded for 429")
                resp.raise_for_status()
                data = resp.json()
                return data.get("data", [])
            except requests.RequestException as e:
                logger.error("Request failed (attempt %d): %s", attempt + 1, e)
                if attempt < max_retries - 1:
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    raise
        return []

    def fetch_reports(
        self,
        limit: int = 100,
        offset: int = 0,
        sort: str = "date.created:desc",
        fields: List[str] = None,
    ) -> List[Dict[str, Any]]:
        return self.fetch("reports", limit=limit, offset=offset, sort=sort, fields=fields)