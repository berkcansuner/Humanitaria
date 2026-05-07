import pytest
from ingestion.parser import parse_report, parse_disaster, parse_country, parse


class TestParseReport:
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
        assert doc["doctype"] == "report"

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
        assert doc["doctype"] == "report"


class TestParseDisaster:
    def test_parse_full_disaster(self):
        raw = {
            "id": "50910",
            "fields": {
                "name": "Benin: Floods - Sep 2021",
                "description": "Heavy rains caused flooding.",
                "date": {"created": "2021-09-06T00:00:00+00:00"},
                "primary_country": {"name": "Benin"},
                "primary_type": {"name": "Flood"},
                "status": "past",
                "glide": "FL-2021-000145-BEN",
                "url": "https://reliefweb.int/taxonomy/term/50910",
            }
        }
        doc = parse_disaster(raw)
        assert doc["title"] == "Benin: Floods - Sep 2021"
        assert doc["body"] == "Heavy rains caused flooding."
        assert doc["country"] == "Benin"
        assert doc["theme"] == "Flood"
        assert doc["format"] == "past"
        assert doc["doctype"] == "disaster"
        assert "50910" in doc["url"]

    def test_parse_disaster_fallback_type(self):
        raw = {
            "id": "99",
            "fields": {
                "name": "Test Disaster",
                "description": "desc",
                "date": {"created": "2026-01-01"},
                "type": [{"name": "Earthquake"}],
            }
        }
        doc = parse_disaster(raw)
        assert doc["theme"] == "Earthquake"
        assert doc["doctype"] == "disaster"

    def test_parse_disaster_no_body(self):
        raw = {
            "id": "100",
            "fields": {
                "name": "No Description",
                "date": {"created": "2026-01-01"},
            }
        }
        doc = parse_disaster(raw)
        assert doc["body"] == ""
        assert doc["doctype"] == "disaster"


class TestParseCountry:
    def test_parse_full_country(self):
        raw = {
            "id": "14894",
            "fields": {
                "name": "Ukraine",
                "description": "Humanitarian overview of Ukraine.",
                "date": {"created": "2014-07-02T16:00:49+00:00"},
                "iso3": "ukr",
                "status": "normal",
                "url": "https://reliefweb.int/taxonomy/term/14894",
            }
        }
        doc = parse_country(raw)
        assert doc["title"] == "Ukraine"
        assert doc["body"] == "Humanitarian overview of Ukraine."
        assert doc["country"] == "Ukraine"
        assert doc["doctype"] == "country"
        assert doc["format"] == "normal"

    def test_parse_country_no_description(self):
        raw = {
            "id": "200",
            "fields": {
                "name": "Qatar",
                "date": {"created": "2026-01-01"},
            }
        }
        doc = parse_country(raw)
        assert doc["title"] == "Qatar"
        assert doc["body"] == ""
        assert doc["country"] == "Qatar"
        assert doc["doctype"] == "country"


class TestParseDispatcher:
    def test_dispatch_reports(self):
        raw = {"id": "1", "fields": {"title": "T", "body": "B"}}
        doc = parse(raw, "reports")
        assert doc["doctype"] == "report"

    def test_dispatch_disasters(self):
        raw = {"id": "2", "fields": {"name": "D", "description": "desc"}}
        doc = parse(raw, "disasters")
        assert doc["doctype"] == "disaster"

    def test_dispatch_countries(self):
        raw = {"id": "3", "fields": {"name": "C"}}
        doc = parse(raw, "countries")
        assert doc["doctype"] == "country"

    def test_dispatch_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown endpoint"):
            parse({}, "nonexistent")