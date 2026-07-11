"""M&E report visual generation (Phase B).

Builds prompts (with baseline safety constraints) and calls the Gemini image API
to produce a cover image + one illustration per top-level report section. Pure rag
layer — no FastAPI/route imports. generate_image() NEVER raises: on the kill-switch
being off, any API error, or a timeout it returns None, so image generation can
never block report generation.
"""
import logging
import re

from config import get_settings

logger = logging.getLogger(__name__)

# Baseline generation-safety constraints, embedded in every prompt. There is no
# visible "AI-generated" label (product decision); these keep the imagery from being
# exploitative, defamatory, or falsely documentary in a humanitarian M&E context.
_SAFETY = (
    "Style: muted, editorial, semi-realistic humanitarian-context illustration. "
    "Constraints: no identifiable real individuals; no fabricated data, numbers, charts, "
    "or map figures rendered in the image; no graphic or undignified depictions of suffering; "
    "no text overlays; no specific real-place claims. Composition only, evocative not documentary."
)

# The indicator report's data table gets no illustration.
_EXCLUDED_HEADINGS = {"indicator table"}


def _call_image_api(prompt: str) -> str:
    """Return raw base64 for the generated image, or raise on failure. Native
    generateContent path with responseModalities=IMAGE (see Task 1 spike)."""
    import httpx
    s = get_settings()
    # GEMINI_IMAGE_BASE_URL must be the native base (…/v1beta or the gateway-native
    # equivalent) — set it in the env per the spike. Fall back to deriving from the
    # OpenAI-compat base by stripping the trailing 'openai/'.
    base = s.GEMINI_IMAGE_BASE_URL or s.GEMINI_BASE_URL.replace("/openai/", "/")
    url = f"{base.rstrip('/')}/models/{s.GEMINI_IMAGE_MODEL}:generateContent"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }
    r = httpx.post(url, params={"key": s.GEMINI_API_KEY}, json=body, timeout=s.GEMINI_IMAGE_TIMEOUT)
    r.raise_for_status()
    for part in r.json()["candidates"][0]["content"]["parts"]:
        if "inlineData" in part:
            return part["inlineData"]["data"]
    raise RuntimeError("no inlineData in image response")


def build_cover_prompt(country: str, theme: str | None, report_type: str) -> str:
    sector = theme or "multi-sector humanitarian situation"
    return (
        f"Cover illustration for a humanitarian monitoring & evaluation report on {country}, "
        f"focused on {sector}. {_SAFETY}"
    )


def build_section_prompt(country: str, theme: str | None, heading: str) -> str:
    sector = theme or "the humanitarian situation"
    return (
        f"Section illustration for '{heading}' in a humanitarian report on {country} "
        f"({sector}). {_SAFETY}"
    )


def extract_section_headings(markdown: str) -> list[str]:
    """Top-level ('## ') headings from the report markdown, excluding the indicator
    data table, capped at REPORT_IMAGE_MAX_SECTIONS."""
    headings = []
    for line in (markdown or "").split("\n"):
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m and not line.startswith("###"):
            h = m.group(1).strip()
            if h.lower() not in _EXCLUDED_HEADINGS:
                headings.append(h)
    cap = get_settings().REPORT_IMAGE_MAX_SECTIONS
    return headings[:cap]


def generate_image(prompt: str) -> str | None:
    """Generate one image; return a 'data:image/png;base64,...' URI, or None on the
    kill-switch being off / any error / timeout. Never raises — the caller stays
    text-only if this returns None."""
    if not get_settings().REPORT_IMAGES_ENABLED:
        return None
    try:
        b64 = _call_image_api(prompt)
        return f"data:image/png;base64,{b64}"
    except Exception as exc:
        logger.warning("Report image generation failed: %s", exc)
        return None
