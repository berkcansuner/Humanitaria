"""Generate a sample M&E report the landing page quotes.

Runs the report pipeline's own pieces (rag.report_service retrieval, rag.chain's
report chain, rag.citations) for one situation report and writes an excerpt to
frontend/src/marketing/data/meReport.<language>.json (by default Syria · Protection and
Human Rights · English, so meReport.en.json): title, type, sector, period, generated
date, two Key Findings sentences verbatim with their [n] markers, and the sources
those sentences cite.

Safety: the database is only read. rag.db.get_engine() would run its schema setup
(ALTER/CREATE/REVOKE) on first use, so the read-only engine of
scripts.generate_landing_answer.use_read_only_db() is installed before anything
connects; any write would fail. The report is never saved to a user account or any
table; the full text goes to a local file (--raw). The report model is called once,
and once more only if that call fails (--max-calls 1: never a second call). The
reranker is switched off (its monthly quota is shared with the live app), so ranking
falls back to the dense/MMR order, as it does when the quota is spent.

When to regenerate: rarely, when the quoted sample report should change. A normal run
COSTS A GEMINI CALL (one report generation); --dry-run stops after retrieval; --reuse
re-excerpts a saved --raw file and costs nothing. Review and commit the file it
writes. The page's other figures come from scripts/build_landing_snapshot.py instead.

Usage:
    python scripts/generate_landing_report.py --raw <path.json>          # generate (en)
    python scripts/generate_landing_report.py --raw <path.json> --reuse  # re-excerpt only
    python scripts/generate_landing_report.py --language tr --raw <path.json>
"""
import argparse
import asyncio
import json
import logging
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)

DATA_DIR = ROOT / "frontend" / "src" / "marketing" / "data"
COUNTRY, THEME, LANGUAGE = "Syrian Arab Republic", "Protection and Human Rights", "en"
REPORT_TYPE = "situation"
MAX_CALLS = 2

_SECTION = re.compile(r"^## +Key Findings\s*$", re.IGNORECASE | re.MULTILINE)
_LEVEL2 = re.compile(r"^## .*$", re.MULTILINE)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ])")
_MARKER = re.compile(r"\[(\d+)\]")


def _has_figure(sentence: str) -> bool:
    return bool(re.search(r"\d", _MARKER.sub("", sentence)))


def key_findings_excerpt(content: str, sources: list[dict], n: int = 2) -> dict:
    """`n` cited sentences of the Key Findings section, verbatim and in report order,
    and the sources they cite (in citation order). Selection rule: going forward through
    the cited sentences, each finding is the next one that states a figure (a digit
    outside its [n] markers) and cites a source no earlier finding cites; failing
    that, the next that cites a new source; failing that, the next cited sentence.
    A report in another language has its headings translated; the prompt fixes the
    order (Executive Summary, Key Findings, Outlook), so there Key Findings is the
    second level-2 section."""
    match = _SECTION.search(content)
    if not match:
        headings = list(_LEVEL2.finditer(content))
        if len(headings) < 2:
            return {"findings": [], "sources": []}
        match = headings[1]
    body = content[match.end():]
    body = body[:m.start()] if (m := re.search(r"^## ", body, re.MULTILINE)) else body

    lines = [line.strip() for line in body.splitlines()]
    candidates = [sentence for line in lines if line and not line.startswith("#")
                  for sentence in _SENTENCE_END.split(line) if _MARKER.search(sentence)]
    findings: list[str] = []
    while candidates and len(findings) < n:
        seen = {num for f in findings for num in _MARKER.findall(f)}
        new = [i for i, s in enumerate(candidates) if set(_MARKER.findall(s)) - seen]
        pick = next((i for i in new if _has_figure(candidates[i])), new[0] if new else 0)
        findings.append(candidates[pick])
        candidates = candidates[pick + 1:]

    by_index = {s["index"]: s for s in sources}
    cited = []
    for sentence in findings:
        for num in map(int, _MARKER.findall(sentence)):
            if num not in cited and num in by_index:
                cited.append(num)
    return {
        "findings": findings,
        "sources": [{"n": i, "publisher": by_index[i].get("source"), "title": by_index[i]["title"],
                     "date": by_index[i].get("date"), "url": by_index[i]["url"]} for i in cited],
    }


async def _generate(country: str, theme: str, language: str, date_from: str, date_to: str,
                    max_calls: int = MAX_CALLS, dry_run: bool = False) -> dict | None:
    os.environ["RERANK_ENABLED"] = "false"
    from config import get_settings
    get_settings.cache_clear()
    from scripts.generate_landing_answer import use_read_only_db
    use_read_only_db()
    from rag.chain import build_report_chain
    from rag.citations import normalize_citations
    from rag.rag_context import _build_context_and_sources
    from rag.report_service import build_report_directive, retrieve_for_report

    docs = await retrieve_for_report(country, theme, date_from, date_to, report_type=REPORT_TYPE)
    if not docs:
        raise SystemExit("No documents retrieved; nothing generated.")
    context, source_dicts = _build_context_and_sources(docs)
    for s in source_dicts:
        logger.info("[%d] %s | %s | %s", s["index"], s.get("date"), s.get("source"), s["title"])
    if dry_run:
        return None
    directive = build_report_directive(country, theme, date_from, date_to, len(docs), language,
                                       report_type=REPORT_TYPE)
    chain = build_report_chain(REPORT_TYPE)  # max_retries=0: one call per ainvoke

    calls, full = 0, None
    while full is None and calls < max_calls:
        calls += 1
        try:
            full = await chain.ainvoke({"question": directive, "context": context})
        except Exception as exc:  # one retry only, then give up
            logger.warning("Report generation call %d failed: %s", calls, exc)
    if full is None:
        raise SystemExit(f"Generation failed after {calls} calls.")
    content, sources = normalize_citations(full, source_dicts)
    return {"generated": date.today().isoformat(), "country": country, "sector": theme,
            "language": language, "date_from": date_from, "date_to": date_to, "calls": calls, "doc_count": len(docs), "content": content, "sources": sources}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw", type=Path, required=True,
                        help="local file for the full generated report (never committed)")
    parser.add_argument("--reuse", action="store_true",
                        help="re-excerpt an existing --raw file without calling the model")
    parser.add_argument("--country", default=COUNTRY, help=f"report country (default {COUNTRY})")
    parser.add_argument("--sector", default=THEME, help=f"report sector/theme (default {THEME})")
    parser.add_argument("--language", choices=("en", "tr"), default=LANGUAGE,
                        help=f"report language; writes meReport.<language>.json (default {LANGUAGE}; "
                             "with --reuse, the raw file's language)")
    parser.add_argument("--max-calls", type=int, choices=(1, 2), default=MAX_CALLS,
                        help="model calls allowed: 2 = one retry if the first call fails")
    parser.add_argument("--dry-run", action="store_true",
                        help="stop after retrieval (no report generated, nothing written)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    language = args.language

    if args.reuse:
        raw = json.loads(args.raw.read_text(encoding="utf-8"))
        # The excerpt is in the raw report's language, so that names the output file.
        language = raw.get("language", language)
    else:
        today = date.today()
        raw = asyncio.run(_generate(args.country, args.sector, language,
                                    (today - timedelta(days=365)).isoformat(), today.isoformat(),
                                    max_calls=args.max_calls, dry_run=args.dry_run))
        if raw is None:
            return
        args.raw.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
        logger.info("Generated with %d model call(s); full report at %s", raw["calls"], args.raw)

    from rag.report_service import report_title
    excerpt = key_findings_excerpt(raw["content"], raw["sources"])
    if len(excerpt["findings"]) < 2:
        raise SystemExit("Key Findings has fewer than two cited sentences; excerpt not written.")
    # A raw file from before --country/--sector/--language carries none of them.
    country = raw.get("country", args.country)
    sector = raw.get("sector", args.sector)
    out = {
        "title": report_title(country, sector, raw["date_from"], raw["date_to"], REPORT_TYPE),
        "country": country, "sector": sector, "type": "Situation report",
        "report_type": REPORT_TYPE,   # the product's key (the page labels it per language)
        "language": language,
        "date_from": raw["date_from"], "date_to": raw["date_to"], "generated": raw["generated"],
        **excerpt,
    }
    out_path = DATA_DIR / f"meReport.{language}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    logger.info("Wrote %s", out_path)


if __name__ == "__main__":
    main()
