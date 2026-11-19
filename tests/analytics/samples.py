"""Findings as compute_findings builds them, for tests that need a report without HAPI."""
from analytics.technical_report import Findings, ReportSection, _adjust_and_describe


def trend(**over) -> dict:
    r = {"kind": "trend", "indicator": "Refugees (people)", "direction": "decreasing",
         "slope": -817000.0, "p_value": 0.734, "pct_change": -38.1, "n_points": 4,
         "ci_low": None, "ci_high": None, "tau": -0.33,
         "first_period": "2022-01-01", "last_period": "2025-01-01", "unit": "",
         "look_back": None, "chosen_from": "2021-11-19",
         "latest_value": 2670000.0, "latest_period": "2025-01-01", "first_value": 5660000.0,
         "periods": ["2022-01-01", "2023-01-01", "2024-01-01", "2025-01-01"],
         "values": [5660000.0, 5700000.0, 4100000.0, 2670000.0],
         "line_change": None, "value_unit": "people", "resolution": "year"}
    return {**r, **over}


def share_trend(**over) -> dict:
    return trend(**{
        "indicator": "Food insecurity (IPC 3+, % of the analysed population)",
        "direction": "decreasing", "slope": -4.65, "p_value": 0.059, "pct_change": -44.7,
        "n_points": 9, "ci_low": -7.99, "ci_high": 0.0, "tau": -0.53,
        "first_period": "2022-03-01", "last_period": "2026-09-01", "unit": "percentage points",
        "latest_value": 32.0, "latest_period": "2026-09-01", "first_value": 47.0,
        "periods": ["2022-03-01", "2026-09-01"], "values": [47.0, 32.0],
        "line_change": -21.0, "value_unit": "%", "resolution": "month", **over})


def snapshot(**over) -> dict:
    r = {"kind": "snapshot", "indicator": "Food security: people in need", "p_value": None,
         "periods": ["2024-01-01", "2025-01-01", "2026-01-01"],
         "values": [15800000.0, 14800000.0, 17400000.0], "value_unit": "people",
         "min_points": 4, "look_back": None, "chosen_from": "2025-11-19",
         "not_comparable": None, "not_comparable_years": None,
         "sector_en": "food security", "sector_tr": "gıda güvenliği",
         "resolution": "year", "exact": False}
    return {**r, **over}


def region(**over) -> dict:
    r = {"kind": "region", "indicator": "Internally displaced people (IDPs)",
         "ranking": [("Herat", 443000.0), ("Balkh", 363000.0), ("Kabul", 310000.0),
                     ("Ghor", 120000.0)],
         "p_value": None, "kruskal_h": None, "max_obs": 1,
         "first_period": "2026-01-01", "last_period": "2026-01-01",
         "value_unit": "people", "resolution": "month"}
    return {**r, **over}


def correlation(**over) -> dict:
    r = {"kind": "correlation", "indicator_x": "Refugees (people)",
         "indicator_y": "Returnees (people)", "coefficient": 0.85, "p_value": 0.004,
         "method": "pearson", "n_points": 8}
    return {**r, **over}


_HEADING = {"trend": "{} — Trend Analysis", "snapshot": "{} — Latest Values",
            "region": "{} — Regional Analysis"}


def findings(*results: dict, **fields) -> Findings:
    """Findings over the given stat results, Holm-adjusted and described like the real
    ones. Extra fields (gaps, notes, headline_items …) go to Findings as given."""
    sections = []
    for r in results:
        heading = (f"Correlation — {r['indicator_x']} ↔ {r['indicator_y']}" if r["kind"] == "correlation"
                   else _HEADING[r["kind"]].format(r["indicator"]))
        sections.append(ReportSection(heading=r.pop("heading", heading), stat_result=r,
                                      chart=None, findings_text=""))
    _adjust_and_describe(sections)
    base = {"gaps": [], "indicators_covered": [], "date_from": "2025-11-19",
            "date_to": "2026-11-19"}
    return Findings(sections=sections, **{**base, **fields})
