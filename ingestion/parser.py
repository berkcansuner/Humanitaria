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
        "source": fields.get("source", {}).get("name", "") if isinstance(fields.get("source"), dict) else "",
        "format": fmt,
    }
