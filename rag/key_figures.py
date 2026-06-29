"""Key-figures extraction for generated M&E reports.

A small, decoupled structured-output call: it reads the FINISHED report prose and
pulls out the 4-6 headline numbers a decision-maker scans first (caseload, severity,
funding, …) as {label, value} pairs for the at-a-glance panel (PDF + UI). Mirrors the
json_mode pattern in rag/query_processor.py. Never blocks report generation — any
failure (timeout, parse, API error) returns an empty list and the panel is simply
omitted.
"""
import logging
from typing import List

from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)


class KeyFigure(BaseModel):
    label: str = Field(description="Short indicator label, e.g. 'People in IPC3+'")
    value: str = Field(description="Compact value, e.g. '19.5M', '41%', '825k', '14 areas'")


class KeyFigures(BaseModel):
    figures: List[KeyFigure] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _accept_bare_list(cls, data):
        # Gemini (json_mode) often returns the bare [{...}, ...] array instead of the
        # wrapped {"figures": [...]} object; wrap it so structured parsing succeeds.
        if isinstance(data, list):
            return {"figures": data}
        return data


_PROMPT = (
    "You extract the key figures from a humanitarian situation report for an at-a-glance panel.\n"
    "Return the 4 to 6 MOST important quantified indicators a decision-maker scans first "
    "(e.g. the overall caseload, the most severe tier, displacement, a critical nutrition figure, "
    "the funding level). For each: a short label (<= 26 characters, e.g. 'People in IPC3+', "
    "'Children with SAM', 'Response funded') and a compact value (e.g. '19.5M', '41%', '825k', "
    "'14 areas', '19%').\n"
    "Rules: use ONLY numbers explicitly stated in the report; never invent or estimate; no citation "
    "markers in the label or value; order by importance; 4-6 figures total.\n\n"
    "Report:\n{content}"
)

_extractor = None


def _get_extractor():
    global _extractor
    if _extractor is None:
        from langchain_openai import ChatOpenAI
        from config import get_settings
        settings = get_settings()
        llm = ChatOpenAI(
            model=settings.GEMINI_QUERY_MODEL,
            base_url=settings.GEMINI_BASE_URL,
            api_key=settings.GEMINI_API_KEY,
            temperature=0.0,
            timeout=10,
        )
        _extractor = llm.with_structured_output(KeyFigures, method="json_mode")
    return _extractor


async def extract_key_figures(content: str, country: str = "", theme: str = "") -> List[dict]:
    """Return up to 6 {label, value} dicts pulled from the report prose, or [] on any failure.

    Decoupled from report generation: called once on the finished content, so a slow or
    failing extraction never delays the prose stream and never breaks the report.
    """
    if not content or not content.strip():
        return []
    try:
        result: KeyFigures = await _get_extractor().ainvoke(_PROMPT.format(content=content))
        out = [
            {"label": f.label.strip(), "value": f.value.strip()}
            for f in result.figures
            if f.label and f.label.strip() and f.value and f.value.strip()
        ]
        return out[:6]
    except Exception as e:  # timeout / parse / API error → panel simply omitted
        logger.warning("Key-figures extraction failed (%s · %s): %s", country, theme, e)
        return []
