"""Snapshot the corpus figures for the public landing page.

Writes frontend/src/marketing/data/coverage.json, which the Vue landing imports at
build time: indexed reports per country (the coverage map's points), the number of
countries, reports and publishers, and the date of the oldest indexed report.

No Gemini calls are made. Database access is SELECT-only: the script opens its own
read-only connection to DATABASE_URL and never runs rag.db's schema setup (which would
ALTER/CREATE on the live database).

When to regenerate: when the corpus has moved enough to show on the page. It reads the
database named by DATABASE_URL (the live one) and ReliefWeb's country list, so it needs
network access. Review and commit the file it writes.

Usage:
    .venv/Scripts/python scripts/build_landing_snapshot.py
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
    return {"counts": counts, "countries": len(counts) - ("World" in counts),
            "reports": total, "publishers": publishers, "since": since}


def _write(name: str, data: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / name).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n",
                                encoding="utf-8")
    logger.info("wrote %s", OUT_DIR / name)


def main() -> None:
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    logging.basicConfig(level=logging.INFO)
    db = _db_figures()
    points = coverage_points(_fetch_countries(), db["counts"])
    _write("coverage.json", {"generated": date.today().isoformat(), "countries": db["countries"],
                             "reports": db["reports"], "publishers": db["publishers"],
                             "since": db["since"], "points": points})


if __name__ == "__main__":
    main()
