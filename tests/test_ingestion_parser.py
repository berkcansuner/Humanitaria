import pytest
from ingestion.parser import parse_report


class TestParser:
    def test_parse_full_report(self):
        raw = {
            "id": "123",
            "fields": {
                "title": "Test Title",
                "body": "Test body content.",
                "date": {"created": "2026-04-01"},
                "source": {"name": "WFP"},
                "primary_country": {"name": "Iran"},
                "theme": [{"name": "Food and Nutrition"}],
                "format": [{"name": "Situation Report"}],
                "file": [{"url": "https://example.com/file.pdf"}]
            }
        }
        doc = parse_report(raw)
        assert doc["title"] == "Test Title"
        assert doc["body"] == "Test body content."
        assert doc["date"] == "2026-04-01"
        assert doc["country"] == "Iran"
        assert doc["theme"] == "Food and Nutrition"
        assert doc["source"] == "WFP"
        assert doc["format"] == "Situation Report"
        assert doc["url"] == "https://example.com/file.pdf"

    def test_parse_missing_optional_fields(self):
        raw = {
            "id": "456",
            "fields": {
                "title": "Minimal",
                "body": "Body only.",
            }
        }
        doc = parse_report(raw)
        assert doc["title"] == "Minimal"
        assert doc["country"] == ""
        assert doc["theme"] == ""
