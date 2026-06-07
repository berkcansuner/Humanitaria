import hashlib
import logging
import re
from typing import Dict, Any, Optional

from ingestion.file_loader import strip_html

logger = logging.getLogger(__name__)


def _normalize_country_name(name: str) -> str:
    """Shorten official country names by removing parenthetical suffixes.

    Examples:
      "Iran (Islamic Republic of)"  → "Iran"
      "Bolivia (Plurinational State of)" → "Bolivia"
      "occupied Palestinian territory"  → unchanged (no parens)
    """
    return re.sub(r'\s*\([^)]+\)\s*$', '', name).strip()


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


def _names(items) -> list:
    """All non-empty 'name' values from a list of dicts (e.g. every theme)."""
    if not isinstance(items, list):
        return []
    out = []
    for it in items:
        if isinstance(it, dict):
            name = _sanitize(it.get("name", ""))
            if name:
                out.append(name)
    return out


def _normalize_date(value: str) -> str:
    """Normalize ReliefWeb date strings to YYYY-MM-DD.

    ReliefWeb returns mixed formats like "2026-04-01" or "2021-09-06T00:00:00+00:00".
    All dates must use the same YYYY-MM-DD format for consistent comparison.
    """
    if not value or not value.strip():
        return ""
    value = value.strip()
    if "T" in value:
        return value[:value.index("T")][:10]
    if len(value) >= 10 and value[4] == "-" and value[7] == "-":
        return value[:10]
    return ""


def parse_report(raw: Dict[str, Any]) -> Dict[str, Any]:
    fields = raw.get("fields") or {}
    # Use the canonical /report/{id} string ONLY to seed doc_id — it is stable
    # across attachment/alias changes and is never visited. (File attachment
    # URLs can change between re-ingests, producing different doc_ids and
    # leaving orphan chunks in the vector store.)
    canonical_url = f"https://reliefweb.int/report/{raw.get('id', '')}"
    doc_id = hashlib.sha256(canonical_url.encode()).hexdigest()
    # Displayed source link must point to the report's REAL web page from the
    # API: url_alias is the readable slug, url is the /node/{id} redirect.
    # The synthesized /report/{id} path 404s on ReliefWeb, so it is never used
    # for the link; the /node/{id} fallback is only for the (now impossible)
    # case where the API returns neither field.
    file_objs = fields.get("file")
    url = (
        _safe_get(fields, "url_alias")
        or _safe_get(fields, "url")
        or f"https://reliefweb.int/node/{raw.get('id', '')}"
    )
    date_field = fields.get("date")
    date = _normalize_date(_safe_get(date_field, "created") if isinstance(date_field, dict) else "")
    country_field = fields.get("primary_country")
    country = _normalize_country_name(_safe_get(country_field, "name")) if isinstance(country_field, dict) else ""
    iso3 = _safe_get(country_field, "iso3").upper() if isinstance(country_field, dict) else ""
    themes = _names(fields.get("theme"))         # ALL sector themes (was first-only)
    theme = themes[0] if themes else ""          # first kept for display/back-compat
    language = _safe_list_get(fields.get("language"), 0, "name")
    glide = _safe_list_get(fields.get("disaster"), 0, "glide")   # linked disaster's GLIDE
    formats = fields.get("format")
    fmt = _safe_list_get(formats, 0, "name")
    source_field = fields.get("source")
    if isinstance(source_field, dict):
        source = _sanitize(source_field.get("name", ""))
    elif isinstance(source_field, list) and source_field:
        source = _safe_list_get(source_field, 0, "name")
    else:
        source = ""
    # pdf_url is stored so the pipeline can optionally fetch richer PDF text
    pdf_url = _safe_get(file_objs[0], "url", "") if file_objs else ""
    return {
        "id": doc_id,
        "url": url,
        "pdf_url": pdf_url,
        "title": _sanitize(fields.get("title", "")),
        "body": strip_html(_sanitize(fields.get("body", ""))),
        "date": date,
        "country": country,
        "iso3": iso3,
        "theme": theme,
        "themes": themes,
        "language": language,
        "glide": glide,
        "source": source,
        "format": fmt,
        "doctype": "report",
    }


def parse_disaster(raw: Dict[str, Any]) -> Dict[str, Any]:
    fields = raw.get("fields") or {}
    url = _safe_get(fields, "url", f"https://reliefweb.int/disasters/{raw.get('id', '')}")
    doc_id = hashlib.sha256(url.encode()).hexdigest()
    date_field = fields.get("date")
    date = _normalize_date(_safe_get(date_field, "created") if isinstance(date_field, dict) else "")
    country_field = fields.get("primary_country")
    country = _normalize_country_name(_safe_get(country_field, "name")) if isinstance(country_field, dict) else ""
    # Disaster TYPE (e.g. "Flood", "Earthquake") is NOT a humanitarian sector theme.
    # Keep it out of `theme` so the sector-theme filter ($eq on report themes like
    # "Health"/"Protection and Human Rights") is not polluted if the disasters
    # endpoint is ingested alongside reports.
    theme = ""
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
    name = _normalize_country_name(_sanitize(fields.get("name", "")))
    url = _safe_get(fields, "url", f"https://reliefweb.int/countries/{raw.get('id', '')}")
    doc_id = hashlib.sha256(url.encode()).hexdigest()
    date_field = fields.get("date")
    date = _normalize_date(_safe_get(date_field, "created") if isinstance(date_field, dict) else "")
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