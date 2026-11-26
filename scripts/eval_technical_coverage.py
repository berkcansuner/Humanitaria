"""How often a technical monitoring report can be produced, and from what.

Runs analytics.technical_report.compute_findings (HDX HAPI only: no model, no
reranker, no database) over countries × sectors × periods and classifies each run
the way api/routes/reports.py answers it, then each section by what it rests on:
a trend inside the chosen period, a trend over a longer look-back, or values shown
untested. Identical HAPI requests are fetched once per run of this script.

    python scripts/eval_technical_coverage.py [--out docs/audit/eval-reports]
"""
import argparse
import csv
import json
import logging
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analytics import technical_report  # noqa: E402
from analytics.countries import iso3_for  # noqa: E402
from analytics.indicators import indicators_for  # noqa: E402

COUNTRIES = [
    "Sudan", "Yemen", "Haiti", "Myanmar", "Burkina Faso", "Ukraine", "Afghanistan",
    "Democratic Republic of the Congo", "Somalia", "South Sudan", "Syrian Arab Republic",
    "Chad", "Mozambique", "Nigeria", "Ethiopia", "Colombia",
]
SECTORS = [None, "Food and Nutrition", "Health", "Protection and Human Rights", "Education",
           "Water Sanitation Hygiene", "Shelter and Non-Food Items"]
PERIODS = {"3m": 91, "12m": 365}


def _cache_fetches():
    seen: dict = {}
    real = technical_report.fetch_rows

    def cached(endpoint, iso3, extra_params=None, **kwargs):
        key = (endpoint, iso3, json.dumps(extra_params or {}, sort_keys=True),
               json.dumps(kwargs, sort_keys=True, default=str))
        if key not in seen:
            try:
                seen[key] = ("ok", real(endpoint, iso3, extra_params=extra_params, **kwargs))
            except Exception as exc:  # replayed below, so a failure counts in every run
                seen[key] = ("err", exc)
        status, value = seen[key]
        if status == "err":
            raise value
        return value

    technical_report.fetch_rows = cached


def outcome(country: str, theme, days: int) -> dict:
    row = {"country": country, "sector": theme or "All sectors", "period": f"{days}d"}
    iso3 = iso3_for(country)
    if iso3 is None:
        return {**row, "outcome": "no_iso3"}
    if theme and not indicators_for(theme):
        return {**row, "outcome": "unsupported_sector"}
    today = date.today()
    f = technical_report.compute_findings(
        iso3, (today - timedelta(days=days)).isoformat(), today.isoformat(), "en", theme)
    kinds = Counter()
    for s in f.sections:
        r = s.stat_result
        kind = r.get("kind")
        if kind in ("trend", "snapshot"):
            kind += "_look_back" if r.get("look_back") else "_in_period"
        kinds[kind] += 1
    gaps = Counter(g["code"] for g in f.gap_items)
    if not f.sections:
        result = ("fetch_failed" if f.failed else "no_sector_data" if theme else "no_findings")
    else:
        result = "report"
    return {**row, "outcome": result, "sections": len(f.sections),
            **{f"sec_{k}": v for k, v in kinds.items()},
            **{f"gap_{k}": v for k, v in gaps.items()},
            "failed": ",".join(f.failed),
            "indicators": ",".join(f.indicators_covered)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="docs/audit/eval-reports")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    _cache_fetches()
    rows = []
    for country in COUNTRIES:
        for theme in SECTORS:
            for label, days in PERIODS.items():
                try:
                    rows.append(outcome(country, theme, days))
                except Exception as exc:
                    rows.append({"country": country, "sector": theme or "All sectors",
                                 "period": f"{days}d", "outcome": "error", "failed": repr(exc)[:200]})
                print(rows[-1]["country"], rows[-1]["sector"], label, rows[-1]["outcome"], flush=True)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    fields = sorted({k for r in rows for k in r}, key=lambda k: (k not in
                    ("country", "sector", "period", "outcome", "sections"), k))
    with open(out / "technical_coverage.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"\n{len(rows)} runs → {out / 'technical_coverage.csv'}")


if __name__ == "__main__":
    main()
