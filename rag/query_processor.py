import logging
import re
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Dict, Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class QueryFilters(BaseModel):
    country: Optional[str] = Field(default=None, description="Canonical ReliefWeb country name")
    theme: Optional[str] = Field(default=None, description="ReliefWeb theme name")
    doctype: Optional[str] = Field(default=None, description="Document type: report, disaster, or country")
    date_from: Optional[str] = Field(default=None, description="ISO date string for lower bound")
    source: Optional[str] = Field(default=None, description="Source organization name")
    format: Optional[str] = Field(default=None, description="Document format")


_COUNTRY_MAP = {
    "iran": "Iran", "ırak": "Iraq", "irak": "Iraq", "suriye": "Syria", "turkey": "Turkey",
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

# Reverse maps for normalization
_CANONICAL_COUNTRIES = set(_COUNTRY_MAP.values())
_CANONICAL_THEMES = set(_THEME_MAP.values())

_FILTER_EXTRACTION_PROMPT = """You are a filter extraction system for a ReliefWeb humanitarian documents database.

Given a user query in Turkish or English, extract structured search filters.

Rules:
- Map country mentions to canonical ReliefWeb names. Examples: gazze/Gaza->State of Palestine, suriye/Syria->Syria, irak/Iraq->Iraq, turkiye/Turkiye->Turkey, somali/Somalia->Somalia, afganistan/Afghanistan->Afghanistan, ukraine/Ukrayna->Ukraine, yemen->Yemen, sudan->Sudan, iran->Iran.
- Map theme mentions to canonical theme names: Food and Nutrition (gida/food/nutrition), Health (saglik/health), Shelter and NFI (barinma/shelter), Water Sanitation Hygiene (su/wash), Protection (koruma/protection), Education (egitim/education), Logistics and Telecommunications (lojistik), Coordination (koordinasyon/coordination).
- Map document type mentions: rapor/report/raporlar/reports -> report, afet/disaster/afetler/disasters -> disaster, ulke/country/ulkeler/countries -> country.
- For source organizations, extract the name as-is (e.g., WFP, UNHCR, OCHA, WHO).
- For format, extract as-is (e.g., Situation Report, Assessment, Map).
- Convert relative dates to absolute ISO format. Today is {today}. Examples: "son 3 ay" / "last 3 months" -> date_from 3 months before today; "last 30 days" / "son 30 gun" -> date_from 30 days before today.
- Only set date_from if the user explicitly mentions a time period or date. If no time reference exists, set date_from to null.
- If a filter type is not mentioned in the query, set it to null.
- Respond ONLY with valid JSON matching the schema.

Query: {query}"""


@lru_cache(maxsize=1)
def _get_llm_extractor():
    from langchain_openai import ChatOpenAI
    from config import get_settings
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.OLLAMA_LLM_MODEL,
        base_url=settings.OLLAMA_CLOUD_BASE_URL,
        api_key=settings.OLLAMA_CLOUD_API_KEY,
        temperature=0.0,
        request_timeout=5,
    )
    return llm.with_structured_output(QueryFilters, method="json_mode")


def _normalize_llm_filters(result: QueryFilters) -> Dict[str, Any]:
    filters: Dict[str, Any] = {}
    if result.country:
        country_lower = result.country.lower()
        if country_lower in _COUNTRY_MAP:
            filters["country"] = _COUNTRY_MAP[country_lower]
        elif result.country in _CANONICAL_COUNTRIES:
            filters["country"] = result.country
        else:
            filters["country"] = result.country
    if result.theme:
        theme_lower = result.theme.lower()
        if theme_lower in _THEME_MAP:
            filters["theme"] = _THEME_MAP[theme_lower]
        elif result.theme in _CANONICAL_THEMES:
            filters["theme"] = result.theme
        else:
            filters["theme"] = result.theme
    if result.doctype:
        doctype_lower = result.doctype.lower()
        if doctype_lower in _DOCTYPE_MAP:
            filters["doctype"] = _DOCTYPE_MAP[doctype_lower]
        else:
            filters["doctype"] = result.doctype
    if result.date_from:
        filters["date"] = {"$gte": result.date_from}
    if result.source:
        filters["source"] = result.source
    if result.format:
        filters["format"] = result.format
    return filters


def _extract_filters_llm(query: str) -> Optional[Dict[str, Any]]:
    try:
        chain = _get_llm_extractor()
        today = datetime.now().strftime("%Y-%m-%d")
        prompt = _FILTER_EXTRACTION_PROMPT.format(today=today, query=query)
        result: QueryFilters = chain.invoke(prompt)
        return _normalize_llm_filters(result)
    except Exception:
        logger.warning("LLM filter extraction failed, falling back to rule-based")
        return None


@lru_cache(maxsize=256)
def _cached_llm_extract(query_normalized: str) -> Optional[Dict[str, Any]]:
    return _extract_filters_llm(query_normalized)


def _extract_filters_rule_based(query: str) -> Dict[str, Any]:
    query_lower = query.replace('İ', 'i').lower()
    filters: Dict[str, Any] = {}
    for key, val in _COUNTRY_MAP.items():
        if key in query_lower:
            filters["country"] = val
            break
    for key, val in _THEME_MAP.items():
        if key in query_lower:
            filters["theme"] = val
            break
    for key, val in _DOCTYPE_MAP.items():
        if key in query_lower:
            filters["doctype"] = val
            break
    # Turkish relative dates
    relative_month = re.search(r"son\s+(\d+)\s+ay", query_lower)
    relative_day = re.search(r"son\s+(\d+)\s+gün", query_lower)
    relative_week = re.search(r"son\s+(\d+)\s+hafta", query_lower)
    # English relative dates
    if not relative_month:
        relative_month = re.search(r"last\s+(\d+)\s+months?", query_lower)
    if not relative_day:
        relative_day = re.search(r"last\s+(\d+)\s+days?", query_lower)
    if not relative_week:
        relative_week = re.search(r"last\s+(\d+)\s+weeks?", query_lower)
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


def extract_filters(query: str) -> Dict[str, Any]:
    query_normalized = query.strip().lower()
    filters = _cached_llm_extract(query_normalized)
    if filters is not None:
        return filters
    return _extract_filters_rule_based(query)