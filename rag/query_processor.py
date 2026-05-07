import re
from datetime import datetime, timedelta
from typing import Dict, Any


# Country name normalization map (common variants)
_COUNTRY_MAP = {
    "iran": "Iran", "ırak": "Iraq", "suriye": "Syria", "turkey": "Turkey",
    "türkiye": "Turkey", "yemen": "Yemen", "afganistan": "Afghanistan",
    "somali": "Somalia", "sudan": "Sudan", "gazze": "State of Palestine",
    "ukraine": "Ukraine", "ukrayna": "Ukraine",
}

_THEME_MAP = {
    "gıda": "Food and Nutrition", "food": "Food and Nutrition", "nutrition": "Food and Nutrition",
    "sağlık": "Health", "health": "Health", "shelter": "Shelter and NFI",
    "barınma": "Shelter and NFI", "su": "Water Sanitation Hygiene", "wash": "Water Sanitation Hygiene",
    "koruma": "Protection", "protection": "Protection",
    "eğitim": "Education", "education": "Education",
    "lojistik": "Logistics and Telecommunications",
    "koordinasyon": "Coordination", "coordination": "Coordination",
}

_DOCTYPE_MAP = {
    "rapor": "report", "report": "report", "raporlar": "report", "reports": "report",
    "afet": "disaster", "disaster": "disaster", "afetler": "disaster", "disasters": "disaster",
    "ülke": "country", "country": "country", "ülkeler": "country", "countries": "country",
    "ulke": "country", "ulkeler": "country",
}


def extract_filters(query: str) -> Dict[str, Any]:
    query_lower = query.replace('İ', 'i').lower()
    filters: Dict[str, Any] = {}
    # Country extraction
    for key, val in _COUNTRY_MAP.items():
        if key in query_lower:
            filters["country"] = val
            break
    # Theme extraction
    for key, val in _THEME_MAP.items():
        if key in query_lower:
            filters["theme"] = val
            break
    # Doctype extraction
    for key, val in _DOCTYPE_MAP.items():
        if key in query_lower:
            filters["doctype"] = val
            break
    # Date extraction (relative only)
    relative_month = re.search(r"son\s+(\d+)\s+ay", query_lower)
    relative_day = re.search(r"son\s+(\d+)\s+gün", query_lower)
    relative_week = re.search(r"son\s+(\d+)\s+hafta", query_lower)
    if relative_month:
        months = int(relative_month.group(1))
        date_from = datetime.now() - timedelta(days=months * 30)
        filters["date"] = {"$gte": date_from.strftime("%Y-%m-%d")}
    elif relative_week:
        weeks = int(relative_week.group(1))
        date_from = datetime.now() - timedelta(weeks=weeks)
        filters["date"] = {"$gte": date_from.strftime("%Y-%m-%d")}
    elif relative_day:
        days = int(relative_day.group(1))
        date_from = datetime.now() - timedelta(days=days)
        filters["date"] = {"$gte": date_from.strftime("%Y-%m-%d")}
    return filters