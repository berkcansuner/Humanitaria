import logging
import time
from typing import List, Dict, Any
import requests
from config import get_settings

logger = logging.getLogger(__name__)

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

    def fetch_reports(
        self,
        limit: int = 100,
        offset: int = 0,
        sort: str = "date.created:desc",
        fields: List[str] = None,
    ) -> List[Dict[str, Any]]:
        if fields is None:
            fields = ["title", "body", "date.created", "source.name",
                      "primary_country.name", "theme.name", "format.name", "file"]
        url = f"{self.base_url}/reports"
        params = {
            "limit": min(limit, 1000),
            "offset": offset,
            "sort": sort,
            "fields": fields,
        }
        max_retries = 5
        backoff = 1.0
        for attempt in range(max_retries):
            try:
                resp = requests.get(url, headers=self.headers, params=params, timeout=30)
                if resp.status_code == 429:
                    logger.warning("Rate limited (429), backing off %.1fs", backoff)
                    time.sleep(backoff)
                    backoff *= 2
                    continue
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
