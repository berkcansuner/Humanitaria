from datetime import date

from scripts.ingest import _resolve_date_from


class TestResolveDateFrom:
    def test_explicit_wins(self):
        # An explicit --date-from is used as-is, ignoring the lookback floor.
        assert _resolve_date_from("2020-05-01", 3, today=date(2026, 6, 2)) == "2020-05-01"

    def test_lookback_floor_applied_when_no_explicit(self):
        assert _resolve_date_from(None, 3, today=date(2026, 6, 2)) == "2023-06-02"

    def test_lookback_zero_disables_floor(self):
        assert _resolve_date_from(None, 0, today=date(2026, 6, 2)) is None

    def test_lookback_negative_disables_floor(self):
        assert _resolve_date_from(None, -1, today=date(2026, 6, 2)) is None

