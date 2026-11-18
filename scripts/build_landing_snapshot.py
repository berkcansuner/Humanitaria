"""Snapshot real figures for the public landing page.

Writes the JSON files that the Vue landing imports at build time:
  frontend/src/marketing/data/coverage.json  (indexed reports per country, for the map)
  frontend/src/marketing/data/sudan.json     (Sudan figures from HDX HAPI, computed in code)
  frontend/src/marketing/data/syria.json     (Syria figures from HDX HAPI, --country SYR)

No Gemini calls are made. Database access is SELECT-only: the script opens its own
read-only connection to DATABASE_URL and never runs rag.db's schema setup (which would
ALTER/CREATE on the live database).

When to regenerate: before a landing release, or when the corpus or the country figures
have moved enough to show on the page. It reads the database named by DATABASE_URL (the
live one), ReliefWeb and HDX HAPI, so it needs network access and costs no model calls.
Review and commit the JSON files it writes.

Usage:
    .venv/Scripts/python scripts/build_landing_snapshot.py                  # coverage + sudan
    .venv/Scripts/python scripts/build_landing_snapshot.py --country SYR    # syria only
"""
import argparse
import json
import logging
import re
import sys
from contextlib import contextmanager
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text  # noqa: E402

logger = logging.getLogger(__name__)

OUT_DIR = ROOT / "frontend" / "src" / "marketing" / "data"
SUDAN = "SDN"
SYRIA = "SYR"


def _reports_for(fields: dict, counts: dict[str, int]) -> int:
    """documents.country holds ReliefWeb's short form ("Iran", "Aruba"), not always `name`."""
    name = fields.get("name") or ""
    for candidate in (name, fields.get("shortname"), re.sub(r"\s*\([^)]*\)\s*$", "", name)):
        if candidate in counts:
            return counts[candidate]
    return 0


def coverage_points(countries: list[dict], counts: dict[str, int]) -> list[dict]:
    """Countries that have a map location and at least one indexed report."""
    points = []
    for item in countries:
        f = item.get("fields", {})
        loc = f.get("location") or {}
        reports = _reports_for(f, counts)
        if loc.get("lat") is None or loc.get("lon") is None or reports <= 0:
            continue
        points.append({"iso3": f["iso3"], "name": f["name"],
                       "lat": loc["lat"], "lon": loc["lon"], "reports": reports})
    return points


def top_regions(ranking: list[tuple[str, float]], n: int = 5) -> list[list]:
    return [[name, round(value)] for name, value in ranking[:n]]


def latest_round_regions(rows: list[dict], ind, period: str, n: int = 5) -> list[list]:
    """Top regions by their value in ONE round (`period`, YYYY-MM-DD), the same round
    as the national latest. `by_region` ranks period means, which would sit beside the
    latest national figure as if they were the same kind of number."""
    from analytics.datasets import regional_series

    in_round = [r for r in rows if str(r.get("reference_period_start"))[:10] == period]
    ranking = sorted(((region, vals[-1]) for region, vals in regional_series(in_round, ind).items()),
                     key=lambda kv: kv[1], reverse=True)
    return top_regions(ranking, n)


def _sig3(p):
    return None if p is None else float(f"{p:.3g}")


def trend_test(stat: dict) -> dict:
    """The technical report's trend result for one indicator, as the landing shows it."""
    return {
        "test": "Mann-Kendall trend test, Sen's slope",
        "direction": stat["direction"],
        "slope_per_year": round(stat["slope"]),
        "p_value": _sig3(stat["p_value"]),
        "p_adjusted": _sig3(stat.get("p_adjusted")),
        "significant": stat.get("significant", False),
        "n_points": stat["n_points"],
        "period": [stat["first_period"][:10], stat["last_period"][:10]],
    }


def peak_window_trend(periods: list[str], values: list[float], min_points: int) -> dict:
    """The technical report's trend test (Sen slope + Mann-Kendall) on the series from
    its peak to its last point. One test, so the Holm adjustment leaves p unchanged."""
    from analytics.stat_tests import ALPHA, holm, trend
    from analytics.technical_report import _years_since_first

    i = max(range(len(values)), key=values.__getitem__)
    window_periods, window_values = periods[i:], values[i:]
    tr = trend(window_values, indicator="IDPs", min_points=min_points,
               times=_years_since_first(window_periods))
    (p_adjusted,) = holm([tr.p_value])
    return trend_test({
        "direction": tr.direction, "slope": tr.slope, "p_value": tr.p_value,
        "p_adjusted": p_adjusted, "significant": p_adjusted is not None and p_adjusted < ALPHA,
        "n_points": tr.n_points, "first_period": window_periods[0],
        "last_period": window_periods[-1],
    })


def latest_by_host(rows: list[dict], n: int = 5) -> list[list] | None:
    """Host (asylum) countries ranked by refugees in the latest round, rows of the same
    round summed. None when there are no rows with a host country."""
    rows = [r for r in rows if r.get("asylum_location_name") and r.get("reference_period_start")]
    if not rows:
        return None
    latest = max(str(r["reference_period_start"])[:10] for r in rows)
    totals: dict[str, float] = {}
    for r in rows:
        if str(r["reference_period_start"])[:10] == latest:
            host = r["asylum_location_name"]
            totals[host] = totals.get(host, 0.0) + float(r["population"])
    return top_regions(sorted(totals.items(), key=lambda kv: kv[1], reverse=True), n)


def funding_by_year(periods: list[str], values: list[float]) -> list[list]:
    """Funding per calendar year (periods of the same year summed), USD to cents."""
    by_year: dict[int, float] = {}
    for p, v in zip(periods, values):
        by_year[int(p[:4])] = by_year.get(int(p[:4]), 0.0) + v
    return [[y, round(v, 2)] for y, v in sorted(by_year.items())]


def pct_change(values: list[float]) -> float | None:
    """Percent change from the first to the last value (None if there is no span)."""
    if len(values) < 2 or not values[0]:
        return None
    return (values[-1] - values[0]) / values[0] * 100


def _fetch_countries() -> list[dict]:
    """ReliefWeb countries (full profile carries `location`); iso3 upper-cased."""
    import requests
    from config import get_settings
    settings = get_settings()
    out, offset = [], 0
    while True:
        for attempt in range(4):   # the full profile is large; the server cuts some responses short
            try:
                resp = requests.get(f"{settings.RELIEFWEB_BASE_URL}/countries", timeout=60, params={
                    "appname": settings.RELIEFWEB_APPNAME, "profile": "full",
                    "limit": 100, "offset": offset})
                resp.raise_for_status()
                page = resp.json().get("data", [])
                break
            except requests.exceptions.RequestException as exc:
                if attempt == 3:
                    raise
                logger.warning("countries page %d failed (%s); retrying", offset, exc)
        for item in page:
            item["fields"]["iso3"] = (item["fields"].get("iso3") or "").upper()
        out += page
        if len(page) < 100:
            return out
        offset += 100


@contextmanager
def _read_only_connection():
    """A SELECT-only connection to DATABASE_URL: its own engine, no schema setup
    (rag.db.get_engine would run CREATE/ALTER on the live database)."""
    from sqlalchemy import create_engine
    from rag.db import _db_url

    engine = create_engine(_db_url())
    try:
        with engine.connect() as conn:
            if engine.dialect.name == "postgresql":
                conn = conn.execution_options(postgresql_readonly=True)
            yield conn
    finally:
        engine.dispose()


def _db_figures() -> dict:
    with _read_only_connection() as conn:
        counts = {r[0]: r[1] for r in conn.execute(text(
            "SELECT country, COUNT(*) FROM documents WHERE country <> '' GROUP BY country"))}
        total, publishers, since = conn.execute(text(
            "SELECT COUNT(*), COUNT(DISTINCT NULLIF(source, '')), MIN(NULLIF(date, '')) "
            "FROM documents")).one()
        figures = {}
        for key, name in (("sudan", "Sudan"), ("syria", "Syrian Arab Republic")):
            n, first = conn.execute(text(
                "SELECT COUNT(*), MIN(NULLIF(date, '')) FROM documents WHERE country = :c"),
                {"c": name}).one()
            figures[key] = {"count": n, "since": first}
    return {"counts": counts, "countries": len(counts) - ("World" in counts),
            "reports": total, "publishers": publishers, "since": since, **figures}


def _series(key: str, date_from: str, today: date, iso3: str = SUDAN):
    """The national series of one indicator, through the same steps as the report.
    Returns (indicator, periods, values, rows) with the filtered rows the series came from."""
    from analytics.datasets import consistent_snapshots, national_series
    from analytics.hapi_client import fetch_rows
    from analytics.indicators import by_key
    from analytics.technical_report import _completed, _filter_period

    ind = by_key(key)
    rows = fetch_rows(ind.endpoint, iso3, extra_params=ind.query_params,
                      admin_level=ind.admin_level, location_param=ind.location_param)
    rows = _filter_period(rows, date_from, today.isoformat())
    if ind.complete_periods_only:
        rows = _completed(rows, today)
    rows, _ = consistent_snapshots(rows)
    periods, values = national_series(rows, ind)
    return ind, periods, values, rows


def _sudan(db_sudan: dict) -> dict:
    from analytics.technical_report import _credit, _years_before, compute_findings
    from config import get_settings

    today = date.today()
    date_from = _years_before(today, get_settings().TECHNICAL_REPORT_DEFAULT_YEARS).isoformat()
    findings = compute_findings(SUDAN, None, None, language="en")
    idp_name = "Internally displaced people (IDPs)"
    trend = next(s.stat_result for s in findings.sections
                 if s.stat_result["kind"] == "trend" and s.stat_result["indicator"] == idp_name)

    ind, periods, values, idp_rows = _series("idps", date_from, today)
    _, ipc_periods, ipc_values, _ = _series("food_security", date_from, today)
    _, fund_periods, fund_values, _ = _series("funding", date_from, today)

    return {
        "generated": today.isoformat(),
        "idps": {"series": [[p[:10], round(v)] for p, v in zip(periods, values)],
                 "credit": _credit(ind, periods[-1], "en"),
                 "pct_change": trend["pct_change"],
                 "trend_test": peak_window_trend(
                     periods, values, get_settings().TECHNICAL_REPORT_MIN_POINTS)},
        "regions": {"period": periods[-1][:10],
                    "top": latest_round_regions(idp_rows, ind, periods[-1][:10])},
        "ipc_share": {"value": round(ipc_values[-1], 1), "period": ipc_periods[-1][:10]},
        "funding": funding_by_year(fund_periods, fund_values),
        "reports": db_sudan,
    }


def _syria(db_syria: dict) -> dict:
    """Syria's landing figures. Returnees and refugees are annual UNHCR counts (one
    round per calendar year); IDPs are IOM DTM rounds; funding is OCHA FTS."""
    from analytics.technical_report import _credit, _years_before
    from config import get_settings

    today = date.today()
    settings = get_settings()
    recent = _years_before(today, settings.TECHNICAL_REPORT_DEFAULT_YEARS).isoformat()
    decade = _years_before(today, 10).isoformat()
    min_points = settings.TECHNICAL_REPORT_MIN_POINTS

    ret, ret_periods, ret_values, _ = _series("returnees", decade, today, SYRIA)
    ref, ref_periods, ref_values, ref_rows = _series("refugees", decade, today, SYRIA)
    idp, idp_periods, idp_values, _ = _series("idps", recent, today, SYRIA)
    _, fund_periods, fund_values, _ = _series("funding", recent, today, SYRIA)

    # Returnees are annual (only 2 points since Dec 2024): too short for the trend test,
    # so the hero card's trend is the UNHCR refugee stock from its peak (5 annual points).
    trend = peak_window_trend(ref_periods, ref_values, min_points)
    trend.update({"series": "refugees", "credit": _credit(ref, ref_periods[-1], "en")})

    return {
        "generated": today.isoformat(),
        "returnees": {"series": [[p[:10], round(v)] for p, v in zip(ret_periods, ret_values)],
                      "credit": _credit(ret, ret_periods[-1], "en"), "period": ret_periods[-1][:4]},
        "refugees": {"latest": round(ref_values[-1]), "period": ref_periods[-1][:4],
                     "credit": _credit(ref, ref_periods[-1], "en"),
                     "by_host": latest_by_host(ref_rows)},
        "funding": funding_by_year(fund_periods, fund_values),
        "idps": {"series": [[p[:10], round(v)] for p, v in zip(idp_periods, idp_values)],
                 "credit": _credit(idp, idp_periods[-1], "en"),
                 "pct_change": pct_change(idp_values),
                 "trend_test": peak_window_trend(idp_periods, idp_values, min_points)},
        "trend": trend,
        "reports": db_syria,
    }


def _write(name: str, data: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / name).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n",
                                encoding="utf-8")
    logger.info("wrote %s", OUT_DIR / name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--country", choices=(SUDAN, SYRIA), default=SUDAN,
                        help="SDN (default): coverage.json + sudan.json; SYR: syria.json only")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    db = _db_figures()
    if args.country == SYRIA:
        _write("syria.json", _syria(db["syria"]))
        return
    points = coverage_points(_fetch_countries(), db["counts"])
    coverage = {"generated": date.today().isoformat(), "countries": db["countries"],
                "reports": db["reports"], "publishers": db["publishers"],
                "since": db["since"], "points": points}
    _write("coverage.json", coverage)
    _write("sudan.json", _sudan(db["sudan"]))


if __name__ == "__main__":
    main()
