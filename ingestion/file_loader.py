import io
import logging
import time
from html.parser import HTMLParser
from typing import Optional

import requests

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

_RETRY_COUNT = 3
_RETRY_BACKOFF_S = 1.0


class _HTMLTextExtractor(HTMLParser):
    """Minimal HTML-to-plain-text extractor using the stdlib parser."""

    _SKIP_TAGS = {"script", "style", "head", "noscript"}

    def __init__(self):
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self._parts.append(stripped)

    def get_text(self) -> str:
        return " ".join(self._parts)


def strip_html(html: str) -> str:
    """Strip HTML tags and return plain text. Falls through for non-HTML strings."""
    if not html or "<" not in html:
        return html
    extractor = _HTMLTextExtractor()
    try:
        extractor.feed(html)
        text = extractor.get_text()
        return " ".join(text.split()) if text else html
    except Exception:
        return html


def fetch_pdf_text(url: str, timeout: int = 30) -> Optional[str]:
    """Download a PDF from *url* and return extracted text, or None on failure."""
    if PdfReader is None:
        logger.warning("pypdf not installed — PDF content extraction skipped")
        return None

    backoff = _RETRY_BACKOFF_S
    for attempt in range(_RETRY_COUNT):
        try:
            resp = requests.get(url, timeout=timeout, headers={"User-Agent": "ReliefWebRAG/1.0"})
            resp.raise_for_status()
            reader = PdfReader(io.BytesIO(resp.content))
            pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text.strip())
            return "\n".join(pages) if pages else None
        except requests.HTTPError as e:
            logger.warning("PDF fetch non-retryable HTTP error for %s: %s", url, e)
            return None
        except Exception as e:
            logger.warning("PDF fetch failed (attempt %d/%d) for %s: %s", attempt + 1, _RETRY_COUNT, url, e)
            if attempt < _RETRY_COUNT - 1:
                time.sleep(backoff)
                backoff *= 2
            else:
                return None
    return None
