import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class QueryFilters(BaseModel):
    country: Optional[str] = Field(default=None, description="Canonical ReliefWeb country name")
    theme: Optional[str] = Field(default=None, description="ReliefWeb theme name")
    doctype: Optional[str] = Field(default=None, description="Document type: report, disaster, or country")
    date_from: Optional[str] = Field(default=None, description="ISO date string for lower bound")
    source: Optional[str] = Field(default=None, description="Source organization name")
    format: Optional[str] = Field(default=None, description="Document format")

    @field_validator("country", "theme", "doctype", "date_from", "source", "format", mode="before")
    @classmethod
    def _coerce_list_to_str(cls, v):
        # Gemini (json_mode) sometimes returns these as single-element lists
        # (e.g. ["Somalia"]) instead of a plain string; take the first element
        # so structured parsing succeeds instead of failing into the fallback.
        if isinstance(v, list):
            return v[0] if v else None
        return v


_COUNTRY_MAP = {
    "iran": "Iran", "ırak": "Iraq", "irak": "Iraq", "suriye": "Syria", "turkey": "Turkey",
    "türkiye": "Turkey", "yemen": "Yemen", "afganistan": "Afghanistan",
    "somali": "Somalia", "sudan": "Sudan", "gazze": "State of Palestine",
    "ukraine": "Ukraine", "ukrayna": "Ukraine",
}

_THEME_MAP = {
    "gıda": "Food and Nutrition", "food": "Food and Nutrition", "nutrition": "Food and Nutrition",
    "sağlık": "Health", "health": "Health", "shelter": "Shelter and Non-Food Items",
    "barınma": "Shelter and Non-Food Items", "su": "Water Sanitation Hygiene", "wash": "Water Sanitation Hygiene",
    "koruma": "Protection and Human Rights", "protection": "Protection and Human Rights",
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


def _as_known_country(value: str) -> Optional[str]:
    """Return the canonical country name if `value` is a known country, else None.

    The small query-processor LLM sometimes drops a country name into the
    `source` field; this lets the caller detect and reclassify that case.
    """
    if not value:
        return None
    v = value.strip().lower()
    if v in _COUNTRY_MAP:
        return _COUNTRY_MAP[v]
    for canon in _CANONICAL_COUNTRIES:
        if canon.lower() == v:
            return canon
    return None

_FILTER_EXTRACTION_PROMPT = """You are a filter extraction system for a ReliefWeb humanitarian documents database.

Given a user query in Turkish or English, extract structured search filters.

Rules:
- Map country mentions to canonical ReliefWeb names. Turkish agglutinative suffixes may be attached
  directly (e.g. "Iranda"/"İran'da" = Iran, "Suriyede" = Syria, "Afganistanda" = Afghanistan).
  Mappings: gazze/Gaza/Gazze -> State of Palestine, suriye/Syria/Suriye/Suriyede -> Syria,
  irak/Iraq/Irak/Irakta -> Iraq, turkiye/Türkiye/Turkey -> Turkey, somali/Somalia/Somali -> Somalia,
  afganistan/Afghanistan -> Afghanistan, ukraine/Ukrayna/Ukraine -> Ukraine,
  yemen/Yemen -> Yemen, sudan/Sudan -> Sudan, iran/Iran/Iranda/Irandaki -> Iran.
- Map SPECIFIC sector keywords to themes. "insani yardım / insani yardim" means "humanitarian aid"
  in general — do NOT assign it to any theme. "gelişmeler/gelismeler", "durum", "kriz", "rapor"
  are also general words — do NOT map them to themes either.
  Theme mappings: Food and Nutrition (gida/food/nutrition), Health (saglik/health),
  Shelter and Non-Food Items (barinma/shelter), Water Sanitation Hygiene (su/wash),
  Protection and Human Rights (koruma/protection), Education (egitim/education),
  Logistics and Telecommunications (lojistik), Coordination (koordinasyon/coordination).
- Map document type mentions: rapor/report/raporlar/reports -> report,
  afet/disaster/afetler/disasters -> disaster, ulke/country/ulkeler/countries -> country.
- For source organizations, extract the name as-is (e.g., WFP, UNHCR, OCHA, WHO).
- For format, extract as-is (e.g., Situation Report, Assessment, Map).
- Convert relative dates to absolute ISO format ONLY when an explicit time unit is given.
  Today is {today}. Examples: "son 3 ay"/"last 3 months" -> 3 months before today;
  "last week"/"son hafta" -> 7 days before today; "last year"/"son yil" -> 1 year before today.
- The following words mean "current/latest" in a vague, non-temporal way and must NOT set
  date_from (set to null):
    Turkish: şu anda, en güncel, güncel, güncel bilgi, mevcut, şimdiki, bugünkü, günümüz,
             hali hazırda, son durum, son gelişmeler, gelişmeler, durum, kriz
    English: currently, right now, at the moment, at this time, most recent, latest, recent,
             up to date, current situation, now, today's, nowadays
- Only set date_from when the query contains explicit patterns like "son X gun/hafta/ay/yil"
  or "last X days/weeks/months/years" or "since DATE" (number + unit required).
- Only set a field if explicitly mentioned in the query. If unclear, set to null.
- Respond ONLY with valid JSON matching the schema.

Query: {query}"""


_llm_extractor = None


def _get_llm_extractor():
    global _llm_extractor
    if _llm_extractor is None:
        from langchain_openai import ChatOpenAI
        from config import get_settings
        settings = get_settings()
        if settings.QUERY_LLM_PROVIDER == "gemini":
            # Gemini via the OpenAI-compatible endpoint — reuses the chat key.
            # A small/fast model is enough for structured filter extraction.
            llm = ChatOpenAI(
                model=settings.GEMINI_QUERY_MODEL,
                base_url=settings.GEMINI_BASE_URL,
                api_key=settings.GEMINI_API_KEY,
                temperature=0.0,
                timeout=10,
            )
        else:
            llm = ChatOpenAI(
                model=settings.OLLAMA_LLM_MODEL,
                base_url=settings.OLLAMA_CLOUD_BASE_URL,
                api_key=settings.OLLAMA_CLOUD_API_KEY,
                temperature=0.0,
                timeout=5,
            )
        _llm_extractor = llm.with_structured_output(QueryFilters, method="json_mode")
    return _llm_extractor


def _normalize_llm_filters(result: QueryFilters) -> Dict[str, Any]:
    filters: Dict[str, Any] = {}
    if result.country:
        country_lower = result.country.lower()
        if country_lower in _COUNTRY_MAP:
            filters["country"] = _COUNTRY_MAP[country_lower]
        else:
            # Accept canonical name or pass through for LLM output
            filters["country"] = result.country
    if result.theme:
        theme_lower = result.theme.lower()
        if theme_lower in _THEME_MAP:
            filters["theme"] = _THEME_MAP[theme_lower]
        else:
            filters["theme"] = result.theme
    if result.doctype:
        doctype_lower = result.doctype.lower()
        if doctype_lower in _DOCTYPE_MAP:
            filters["doctype"] = _DOCTYPE_MAP[doctype_lower]
        else:
            filters["doctype"] = result.doctype
    if result.date_from:
        try:
            from_date = datetime.strptime(result.date_from[:10], "%Y-%m-%d").date()
            today = datetime.now().date()
            if from_date >= today:
                # date_from = today or future is meaningless (ingested docs are always a few
                # days old). LLM interpreted vague words like "şu anda"/"currently" as today.
                logger.debug(
                    "LLM returned date_from=%s (today or future) — ignoring to avoid "
                    "filtering out all documents",
                    result.date_from,
                )
            else:
                filters["date"] = {"$gte": result.date_from[:10]}
        except ValueError:
            pass  # malformed date → ignore
    if result.source:
        # The tiny LLM sometimes misclassifies a country as a source; a source
        # filter on a country name returns zero documents, so reclassify it.
        promoted = _as_known_country(result.source)
        if promoted:
            filters.setdefault("country", promoted)
        else:
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
    except Exception as e:
        logger.warning("LLM filter extraction failed, falling back to rule-based: %s", e)
        return None


_llm_cache: Dict[str, Dict[str, Any]] = {}
_MAX_LLM_CACHE = 512


def _cached_llm_extract(query_normalized: str) -> Optional[Dict[str, Any]]:
    if query_normalized in _llm_cache:
        return _llm_cache[query_normalized]
    result = _extract_filters_llm(query_normalized)
    if result is not None:
        if len(_llm_cache) >= _MAX_LLM_CACHE:
            oldest_key = next(iter(_llm_cache))
            del _llm_cache[oldest_key]
        _llm_cache[query_normalized] = result
    return result


def _turkish_lower(text: str) -> str:
    """Lowercase with Turkish-aware character mapping for consistent matching."""
    return (
        text
        .replace("İ", "i").replace("Ü", "u").replace("Ö", "o")
        .replace("Ş", "s").replace("Ç", "c").replace("Ğ", "g")
        .lower()
    )


def _match_word(keyword: str, text: str) -> bool:
    """Return True if keyword appears as a word (or word-prefix for long keywords) in text.

    Short keywords (≤3 chars, e.g. 'su') use exact word boundaries to avoid false
    positives. Longer keywords use only a START boundary so Turkish agglutinative
    suffixes are accepted: 'iran' matches 'iranda' (İran'da), 'irandan' (from Iran).
    """
    if len(keyword) <= 3:
        return bool(re.search(r"\b" + re.escape(keyword) + r"\b", text))
    return bool(re.search(r"\b" + re.escape(keyword), text))


def _extract_filters_rule_based(query: str) -> Dict[str, Any]:
    query_lower = _turkish_lower(query)
    filters: Dict[str, Any] = {}

    for key, val in _COUNTRY_MAP.items():
        if _match_word(key, query_lower):
            filters["country"] = val
            break
    for key, val in _THEME_MAP.items():
        if _match_word(key, query_lower):
            filters["theme"] = val
            break
    for key, val in _DOCTYPE_MAP.items():
        if _match_word(key, query_lower):
            filters["doctype"] = val
            break

    # --- Date extraction (ordered by specificity) ---

    # "since YYYY-MM-DD" / "since M/D/YYYY" / Turkish "YYYY-MM-DD'den beri"
    since_date = re.search(
        r"\bsince\s+(\d{4}-\d{2}-\d{2})\b"
        r"|\bsince\s+(\d{1,2}/\d{1,2}/\d{4})\b"
        r"|(\d{4}-\d{2}-\d{2})\s*(?:'den|'dan|den|dan)\s*beri",
        query_lower,
    )

    # Numbered relative dates
    relative_month = re.search(r"son\s+(\d+)\s+ay", query_lower)
    relative_day = re.search(r"son\s+(\d+)\s+gun", query_lower)
    relative_week = re.search(r"son\s+(\d+)\s+hafta", query_lower)
    if not relative_month:
        relative_month = re.search(r"last\s+(\d+)\s+months?", query_lower)
    if not relative_day:
        relative_day = re.search(r"last\s+(\d+)\s+days?", query_lower)
    if not relative_week:
        relative_week = re.search(r"last\s+(\d+)\s+weeks?", query_lower)

    # Numberless relative dates
    relative_week_no_num = re.search(r"\b(son|gecen)\s+hafta\b", query_lower) or re.search(r"\blast\s+week\b", query_lower)
    relative_month_no_num = re.search(r"\b(son|gecen)\s+ay\b", query_lower) or re.search(r"\blast\s+month\b", query_lower)

    # Specific periods
    yesterday_match = re.search(r"\b(yesterday|dun)\b", query_lower)
    today_match = re.search(r"\b(today|bugun)\b", query_lower)
    this_week = re.search(r"\b(this\s+week|bu\s+hafta)\b", query_lower)
    this_month = re.search(r"\b(this\s+month|bu\s+ay)\b", query_lower)
    recent = re.search(r"\b(recent|son\s+donem|guncel|son\s+zamanlar)\b", query_lower)

    # Apply date filter in priority order (use relativedelta for accurate month arithmetic)
    now = datetime.now()
    if since_date:
        date_str = since_date.group(1) or since_date.group(2) or since_date.group(3)
        if "/" in date_str:
            date_from = datetime.strptime(date_str, "%m/%d/%Y")
            filters["date"] = {"$gte": date_from.strftime("%Y-%m-%d")}
        else:
            filters["date"] = {"$gte": date_str}
    elif relative_month:
        months = int(relative_month.group(1))
        date_from = now - relativedelta(months=months)
        filters["date"] = {"$gte": date_from.strftime("%Y-%m-%d")}
    elif relative_week:
        weeks = int(relative_week.group(1))
        date_from = now - timedelta(weeks=weeks)
        filters["date"] = {"$gte": date_from.strftime("%Y-%m-%d")}
    elif relative_day:
        days = int(relative_day.group(1))
        date_from = now - timedelta(days=days)
        filters["date"] = {"$gte": date_from.strftime("%Y-%m-%d")}
    elif relative_month_no_num:
        date_from = now - relativedelta(months=1)
        filters["date"] = {"$gte": date_from.strftime("%Y-%m-%d")}
    elif relative_week_no_num:
        date_from = now - timedelta(weeks=1)
        filters["date"] = {"$gte": date_from.strftime("%Y-%m-%d")}
    elif this_month:
        date_from = now.replace(day=1)
        filters["date"] = {"$gte": date_from.strftime("%Y-%m-%d")}
    elif this_week:
        days_since_monday = now.weekday()
        date_from = now - timedelta(days=days_since_monday)
        filters["date"] = {"$gte": date_from.strftime("%Y-%m-%d")}
    elif yesterday_match:
        date_from = now - timedelta(days=1)
        filters["date"] = {"$gte": date_from.strftime("%Y-%m-%d")}
    elif today_match:
        date_from = now
        filters["date"] = {"$gte": date_from.strftime("%Y-%m-%d")}
    elif recent:
        date_from = now - relativedelta(months=1)
        filters["date"] = {"$gte": date_from.strftime("%Y-%m-%d")}
    return filters


def extract_filters(query: str) -> Dict[str, Any]:
    query_normalized = _turkish_lower(query.strip())
    llm_filters = _cached_llm_extract(query_normalized)
    rule_filters = _extract_filters_rule_based(query)
    if llm_filters is None:
        # LLM call failed entirely → rely on the deterministic extractor.
        return rule_filters
    # The small LLM is unreliable and often returns empty/partial output. Use the
    # rule-based extractor as a backstop: it fills the curated country/theme/doctype/
    # date fields the LLM left empty, while the LLM still wins on any field it set.
    merged = dict(rule_filters)
    merged.update(llm_filters)
    return merged


_SUGGESTION_COUNTRIES = [
    "Iran", "Syria", "Yemen", "Ukraine", "Turkey",
    "Afghanistan", "Somalia", "Sudan", "State of Palestine", "Iraq",
]

_SUGGESTION_THEMES = [
    "Food and Nutrition", "Health", "Shelter and Non-Food Items",
    "Water Sanitation Hygiene", "Protection and Human Rights", "Education",
    "Logistics and Telecommunications", "Coordination",
]

_SUGGESTION_TIME_PERIODS = [
    "son 1 hafta", "son 1 ay", "son 3 ay", "son 1 yıl",
    "last week", "last month", "last 3 months", "last year",
]


def analyze_query(query: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Detect whether a query is vague and provide clarification suggestions."""
    if filters is None:
        filters = extract_filters(query)
    has_country = "country" in filters
    has_date = "date" in filters
    has_theme = "theme" in filters
    is_vague = not (has_country or has_date or has_theme)

    result: Dict[str, Any] = {
        "has_country": has_country,
        "has_date": has_date,
        "has_theme": has_theme,
        "is_vague": is_vague,
        "suggestions": {
            "countries": _SUGGESTION_COUNTRIES if not has_country else [],
            "time_periods": _SUGGESTION_TIME_PERIODS if not has_date else [],
            "themes": _SUGGESTION_THEMES if not has_theme else [],
        },
    }

    if is_vague:
        result["message"] = "Hangi ülke, zaman aralığı veya konu hakkında bilgi almak istiyorsunuz?"
    elif not has_country and not has_date:
        result["message"] = "Hangi ülke ve zaman aralığı hakkında bilgi almak istiyorsunuz?"
    elif not has_country:
        result["message"] = "Hangi ülke hakkında bilgi almak istiyorsunuz?"
    elif not has_date:
        result["message"] = "Hangi zaman aralığı hakkında bilgi almak istiyorsunuz?"
    elif not has_theme:
        result["message"] = "Hangi konu hakkında bilgi almak istiyorsunuz?"
    else:
        result["message"] = ""

    return result
