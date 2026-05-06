import pytest
from datetime import datetime, timedelta
from rag.query_processor import extract_filters


class TestQueryProcessor:
    def test_extract_country(self):
        f = extract_filters("İran'daki gıda durumu")
        assert f.get("country") == "Iran"

    def test_extract_theme_food(self):
        f = extract_filters("gıda sektörü raporları")
        assert f.get("theme") == "Food and Nutrition"

    def test_extract_date_relative(self):
        f = extract_filters("son 1 ayda olanlar")
        assert "date" in f
        from datetime import date
        parsed = datetime.strptime(f["date"]["$gte"], "%Y-%m-%d").date()
        assert (date.today() - parsed).days >= 29

    def test_no_filters(self):
        f = extract_filters("başa çıkma stratejileri")
        assert f == {}
