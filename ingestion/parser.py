import hashlib
from typing import Dict, Any


def parse_report(raw: Dict[str, Any]) -> Dict[str, Any]:
    fields = raw.get("fields", {})
    file_objs = fields.get("file", [])
    url = file_objs[0].get("url", "") if file_objs else f"https://reliefweb.int/report/{raw.get('id', '')}"
    doc_id = hashlib.sha256(url.encode()).hexdigest()
    date_field = fields.get("date", {})
    date = date_field.get("created", "") if isinstance(date_field, dict) else ""
    country_field = fields.get("primary_country", {})
    country = country_field.get("name", "") if isinstance(country_field, dict) else ""
    themes = fields.get("theme", [])
    theme = themes[0].get("name", "") if isinstance(themes, list) and themes else ""
    formats = fields.get("format", [])
    fmt = formats[0].get("name", "") if isinstance(formats, list) and formats else ""
    return {
        "id": doc_id,
        "url": url,
        "title": fields.get("title", ""),
        "body": fields.get("body", ""),
        "date": date,
        "country": country,
        "theme": theme,
        "source": (
            fields.get("source", {}).get("name", "")
            if isinstance(fields.get("source"), dict)
            else (
                fields.get("source", [])[0].get("name", "")
                if isinstance(fields.get("source"), list) and fields.get("source")
                else ""
            )
        ),
        "format": fmt,
        "doctype": "report",
    }


def parse_disaster(raw: Dict[str, Any]) -> Dict[str, Any]:
    fields = raw.get("fields", {})
    url = fields.get("url", f"https://reliefweb.int/disasters/{raw.get('id', '')}")
    doc_id = hashlib.sha256(url.encode()).hexdigest()
    date_field = fields.get("date", {})
    date = date_field.get("created", "") if isinstance(date_field, dict) else ""
    country_field = fields.get("primary_country", {})
    country = country_field.get("name", "") if isinstance(country_field, dict) else ""
    primary_type = fields.get("primary_type", {})
    theme = primary_type.get("name", "") if isinstance(primary_type, dict) else ""
    if not theme:
        types = fields.get("type", [])
        theme = types[0].get("name", "") if isinstance(types, list) and types else ""
    return {
        "id": doc_id,
        "url": url,
        "title": fields.get("name", ""),
        "body": fields.get("description", ""),
        "date": date,
        "country": country,
        "theme": theme,
        "source": "",
        "format": fields.get("status", ""),
        "doctype": "disaster",
    }


def parse_country(raw: Dict[str, Any]) -> Dict[str, Any]:
    fields = raw.get("fields", {})
    name = fields.get("name", "")
    url = fields.get("url", f"https://reliefweb.int/countries/{raw.get('id', '')}")
    doc_id = hashlib.sha256(url.encode()).hexdigest()
    date_field = fields.get("date", {})
    date = date_field.get("created", "") if isinstance(date_field, dict) else ""
    return {
        "id": doc_id,
        "url": url,
        "title": name,
        "body": fields.get("description", ""),
        "date": date,
        "country": name,
        "theme": "",
        "source": "",
        "format": fields.get("status", ""),
        "doctype": "country",
    }


_PARSERS = {
    "reports": parse_report,
    "disasters": parse_disaster,
    "countries": parse_country,
}


def parse(raw: Dict[str, Any], endpoint: str) -> Dict[str, Any]:
    parser = _PARSERS.get(endpoint)
    if parser is None:
        raise ValueError(f"Unknown endpoint: {endpoint}. Must be one of: {list(_PARSERS)}")
    return parser(raw)