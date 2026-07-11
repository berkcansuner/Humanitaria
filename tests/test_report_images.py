"""Tests for rag.report_images — report visual generation (Phase B).

The real Gemini image API is always mocked; no test generates a real image.
"""
from unittest.mock import MagicMock, patch


def _settings(enabled=True, max_sections=6):
    s = MagicMock()
    s.GEMINI_IMAGE_MODEL = "gemini-3.1-flash-image"
    s.GEMINI_IMAGE_BASE_URL = ""
    s.GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
    s.GEMINI_API_KEY = "test-key"
    s.GEMINI_IMAGE_TIMEOUT = 30
    s.REPORT_IMAGES_ENABLED = enabled
    s.REPORT_IMAGE_MAX_SECTIONS = max_sections
    return s


class TestPromptBuilders:
    def test_cover_prompt_includes_scope_and_safety(self):
        from rag.report_images import build_cover_prompt
        p = build_cover_prompt("Sudan", "Food and Nutrition", "situation")
        assert "Sudan" in p and "Food and Nutrition" in p
        # baseline safety constraints must be embedded
        low = p.lower()
        assert "no identifiable" in low or "no recognizable" in low
        assert "no fabricated" in low or "no invented" in low

    def test_section_prompt_includes_heading_and_safety(self):
        from rag.report_images import build_section_prompt
        p = build_section_prompt("Mali", None, "Priority Needs by Sector")
        assert "Mali" in p and "Priority Needs by Sector" in p
        assert "no fabricated" in p.lower() or "no invented" in p.lower()


class TestExtractSectionHeadings:
    def test_extracts_level2_headings(self):
        from rag.report_images import extract_section_headings
        md = "# Title\n\n## Overview\ntext\n\n## Key Findings\ntext\n\n### Sub\nx\n"
        with patch("rag.report_images.get_settings", return_value=_settings()):
            assert extract_section_headings(md) == ["Overview", "Key Findings"]

    def test_excludes_indicator_table(self):
        from rag.report_images import extract_section_headings
        md = "## Overview\nx\n## Indicator Table\n| a |\n## Data Gaps\nx\n"
        with patch("rag.report_images.get_settings", return_value=_settings()):
            assert extract_section_headings(md) == ["Overview", "Data Gaps"]

    def test_caps_at_max_sections(self):
        from rag.report_images import extract_section_headings
        md = "".join(f"## S{i}\ntext\n" for i in range(10))
        with patch("rag.report_images.get_settings", return_value=_settings(max_sections=3)):
            assert len(extract_section_headings(md)) == 3


class TestCallImageApiAuth:
    def test_key_sent_via_header_not_query_param(self):
        # Regression: the API key must never appear in the request URL/params, since
        # httpx.HTTPStatusError's message embeds the full URL and that message gets
        # logged verbatim on failure (log-leak of the same key used for chat+embeddings).
        from rag import report_images

        fake_response = MagicMock()
        fake_response.raise_for_status.return_value = None
        fake_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"inlineData": {"data": "AAA"}}]}}]
        }
        with patch("rag.report_images.get_settings", return_value=_settings()), \
             patch("httpx.post", return_value=fake_response) as mock_post:
            out = report_images._call_image_api("p")
        assert out == "AAA"
        _, kwargs = mock_post.call_args
        assert "key" not in kwargs.get("params", {})
        assert kwargs["headers"]["x-goog-api-key"] == "test-key"


class TestGenerateImage:
    def test_returns_none_when_disabled(self):
        from rag.report_images import generate_image
        with patch("rag.report_images.get_settings", return_value=_settings(enabled=False)):
            assert generate_image("anything") is None

    def test_returns_data_uri_on_success(self):
        from rag import report_images
        # b64 for a 1-byte payload; the function must wrap it as a data URI.
        fake_b64 = "iVBORw0KGgo="
        with patch("rag.report_images.get_settings", return_value=_settings()), \
             patch("rag.report_images._call_image_api", return_value=fake_b64):
            out = report_images.generate_image("prompt")
        assert out == f"data:image/png;base64,{fake_b64}"

    def test_returns_none_on_api_error(self):
        from rag import report_images
        with patch("rag.report_images.get_settings", return_value=_settings()), \
             patch("rag.report_images._call_image_api", side_effect=RuntimeError("boom")):
            assert report_images.generate_image("prompt") is None
