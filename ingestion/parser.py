import hashlib
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def _sanitize(value) -> str:
    """Ensure a value is a string; convert None or non-string to empty string."""
    if isinstance(value, str):
        return value
    return ""


def _safe_get(obj, key, default=""):
    """Safe dict.get that handles None obj and sanitizes result."""
    if obj is None or not isinstance(obj, dict):
        return _sanitize(default) if default is not None else ""
    return _sanitize(obj.get(key, default))


def _safe_list_get(items, index=0, key="name", default=""):
    """Safely get a value from a list of dicts. Returns default on any failure."""
    if not items or not isinstance(items, list) or index >= len(items):
        return default
    item = items[index]
    if not isinstance(item, dict):
        return default
    return _sanitize(item.get(key, default))


def parse_report(raw: Dict[str, Any]) -> Dict[str, Any]:
    fields = raw.get("fields") or {}
    file_objs = fields.get("file")
    if file_objs and isinstance(file_objs, list) and len(file_objs) > 0:
        url = _safe_get(file_objs[0], "url", f"https://reliefweb.int/report/{raw.get('id', '')}")
    else:
        url = f"https://reliefweb.int/report/{raw.get('id', '')}"
    doc_id = hashlib.sha256(url.encode()).hexdigest()
    date_field = fields.get("date")
    date = _safe_get(date_field, "created") if isinstance(date_field, dict) else ""
    country_field = fields.get("primary_country")
    country = _safe_get(country_field, "name") if isinstance(country_field, dict) else ""
    themes = fields.get("theme")
    theme = _safe_list_get(themes, 0, "name")
    formats = fields.get("format")
    fmt = _safe_list_get(formats, 0, "name")
    source_field = fields.get("source")
    if isinstance(source_field, dict):
        source = _sanitize(source_field.get("name", ""))
    elif isinstance(source_field, list) and source_field:
        source = _safe_list_get(source_field, 0, "name")
    else:
        source = ""
    return {
        "id": doc_id,
        "url": url,
        "title": _sanitize(fields.get("title", "")),
        "body": _sanitize(fields.get("body", "")),
        "date": date,
        "country": country,
        "theme": theme,
        "source": source,
        "format": fmt,
        "doctype": "report",
    }


def parse_disaster(raw: Dict[str, Any]) -> Dict[str, Any]:
    fields = raw.get("fields") or {}
    url = _safe_get(fields, "url", f"https://reliefweb.int/disasters/{raw.get('id', '')}")
    doc_id = hashlib.sha256(url.encode()).hexdigest()
    date_field = fields.get("date")
    date = _safe_get(date_field, "created") if isinstance(date_field, dict) else ""
    country_field = fields.get("primary_country")
    country = _safe_get(country_field, "name") if isinstance(country_field, dict) else ""
    primary_type = fields.get("primary_type")
    theme = _safe_get(primary_type, "name") if isinstance(primary_type, dict) else ""
    if not theme:
        types = fields.get("type")
        theme = _safe_list_get(types, 0, "name")
    return {
        "id": doc_id,
        "url": url,
        "title": _sanitize(fields.get("name", "")),
        "body": _sanitize(fields.get("description", "")),
        "date": date,
        "country": country,
        "theme": theme,
        "source": "",
        "format": _sanitize(fields.get("status", "")),
        "doctype": "disaster",
    }


def parse_country(raw: Dict[str, Any]) -> Dict[str, Any]:
    fields = raw.get("fields") or {}
    name = _sanitize(fields.get("name", ""))
    url = _safe_get(fields, "url", f"https://reliefweb.int/countries/{raw.get('id', '')}")
    doc_id = hashlib.sha256(url.encode()).hexdigest()
    date_field = fields.get("date")
    date = _safe_get(date_field, "created") if isinstance(date_field, dict) else ""
    return {
        "id": doc_id,
        "url": url,
        "title": name,
        "body": _sanitize(fields.get("description", "")),
        "date": date,
        "country": name,
        "theme": "",
        "source": "",
        "format": _sanitize(fields.get("status", "")),
        "doctype": "country",
    }


_PARSERS = {
    "reports": parse_report,
    "disasters": parse_disaster,
    "countries": parse_country,
}


def parse(raw: Dict[str, Any], endpoint: str) -> Optional[Dict[str, Any]]:
    parser = _PARSERS.get(endpoint)
    if parser is None:
        raise ValueError(f"Unknown endpoint: {endpoint}. Must be one of: {list(_PARSERS)}")
    try:
        return parser(raw)
    except Exception as e:
        logger.warning("Parse error for endpoint %s: %s", endpoint, e)
        return None