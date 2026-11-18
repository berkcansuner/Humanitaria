"""Generate the one sample M&E report the landing page quotes.

Runs the report pipeline's own pieces (rag.report_service retrieval, rag.chain's
report chain, rag.citations) for one situation report and writes an excerpt to
frontend/src/marketing/data/meReport.json: title, type, sector, period, generated
date, two Key Findings sentences verbatim with their [n] markers, and the sources
those sentences cite.

Safety: the database is only read (retrieval). The report is never saved to a user
account or any table; the full text goes to a local file (--raw). The report model is
called once, and once more only if that call fails. The reranker is switched off
(its monthly quota is shared with the live app), so ranking falls back to the
dense/MMR order, as it does when the quota is spent.

Usage:
    python scripts/generate_landing_report.py --raw <path.json>          # generate
    python scripts/generate_landing_report.py --raw <path.json> --reuse  # re-excerpt only
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

OUT = ROOT / "frontend" / "src" / "marketing" / "data" / "meReport.json"
COUNTRY, THEME, LANGUAGE, REPORT_TYPE = "Sudan", "Health", "en", "situation"
MAX_CALLS = 2

_SECTION = re.compile(r"^## +Key Findings\s*$", re.IGNORECASE | re.MULTILINE)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
_MARKER = re.compile(r"\[(\d+)\]")


def key_findings_excerpt(content: str, sources: list[dict], n: int = 2) -> dict:
    """The first `n` sentences of the Key Findings section that cite a source, verbatim,
    and the sources they cite (in citation order)."""
    match = _SECTION.search(content)
    if not match:
        return {"findings": [], "sources": []}
    body = content[match.end():]
    body = body[:m.start()] if (m := re.search(r"^## ", body, re.MULTILINE)) else body

    findings = []
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for sentence in _SENTENCE_END.split(line):
            if _MARKER.search(sentence) and len(findings) < n:
                findings.append(sentence)

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


async def _generate(date_from: str, date_to: str) -> dict:
    os.environ["RERANK_ENABLED"] = "false"
    from rag.chain import build_report_chain
    from rag.citations import normalize_citations
    from rag.rag_context import _build_context_and_sources
    from rag.report_service import build_report_directive, retrieve_for_report

    docs = await retrieve_for_report(COUNTRY, THEME, date_from, date_to, report_type=REPORT_TYPE)
    if not docs:
        raise SystemExit("No documents retrieved; nothing generated.")
    context, source_dicts = _build_context_and_sources(docs)
    directive = build_report_directive(COUNTRY, THEME, date_from, date_to, len(docs), LANGUAGE,
                                       report_type=REPORT_TYPE)
    chain = build_report_chain(REPORT_TYPE)  # max_retries=0: one call per ainvoke

    calls, full = 0, None
    while full is None and calls < MAX_CALLS:
        calls += 1
        try:
            full = await chain.ainvoke({"question": directive, "context": context})
        except Exception as exc:  # one retry only, then give up
            logger.warning("Report generation call %d failed: %s", calls, exc)
    if full is None:
        raise SystemExit(f"Generation failed after {calls} calls.")
    content, sources = normalize_citations(full, source_dicts)
    return {"generated": date.today().isoformat(), "date_from": date_from, "date_to": date_to,
            "calls": calls, "doc_count": len(docs), "content": content, "sources": sources}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw", type=Path, required=True,
                        help="local file for the full generated report (never committed)")
    parser.add_argument("--reuse", action="store_true",
                        help="re-excerpt an existing --raw file without calling the model")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.reuse:
        raw = json.loads(args.raw.read_text(encoding="utf-8"))
    else:
        today = date.today()
        raw = asyncio.run(_generate((today - timedelta(days=365)).isoformat(), today.isoformat()))
        args.raw.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
        logger.info("Generated with %d model call(s); full report at %s", raw["calls"], args.raw)

    from rag.report_service import report_title
    excerpt = key_findings_excerpt(raw["content"], raw["sources"])
    if len(excerpt["findings"]) < 2:
        raise SystemExit("Key Findings has fewer than two cited sentences; excerpt not written.")
    out = {
        "title": report_title(COUNTRY, THEME, raw["date_from"], raw["date_to"], REPORT_TYPE),
        "country": COUNTRY, "sector": THEME, "type": "Situation report", "language": LANGUAGE,
        "date_from": raw["date_from"], "date_to": raw["date_to"], "generated": raw["generated"],
        **excerpt,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    logger.info("Wrote %s", OUT)


if __name__ == "__main__":
    main()
