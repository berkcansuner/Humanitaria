"""Report-type evaluation, stage 1: frozen evidence packets and the reports built on them.

    python scripts/eval_reports.py packets    # 1 rerank request per packet (5 in all)
    python scripts/eval_reports.py generate   # 18 Gemini report calls (about 27 TRY)
    python scripts/eval_reports.py check      # deterministic measures, no external call

Each packet is retrieved once with the production path (rag.report_service.
retrieve_for_report, top 16) and saved, so every report type reads the same
documents: situation and needs assessment take the first 12, indicator monitoring
all 16, as production does (the ranking does not depend on top_k, so 12 is a prefix
of 16). Reports are generated with the production prompts and citation clean-up
and written to files, never to the database. The database is opened read-only
through an engine of this script's own: rag.db's schema set-up never runs.
"""
import argparse
import asyncio
import json
import os
import re
import sys
import time
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

OUT = Path("docs/audit/eval-reports")

# Dates are frozen when the packets are first retrieved (see `packets`).
PACKETS = {
    "sudan_food_3m": {"country": "Sudan", "theme": "Food and Nutrition", "days": 91},
    "yemen_health_6m": {"country": "Yemen", "theme": "Health", "days": 182},
    "haiti_protection_3m": {"country": "Haiti", "theme": "Protection and Human Rights", "days": 91},
    "myanmar_all_12m": {"country": "Myanmar", "theme": None, "days": 365},
    "burkina_all_3m": {"country": "Burkina Faso", "theme": None, "days": 91},
}
SCENARIOS = {
    "S1": ("sudan_food_3m", "en"),
    "S2": ("yemen_health_6m", "en"),
    "S3": ("yemen_health_6m", "tr"),
    "S4": ("haiti_protection_3m", "tr"),
    "S5": ("myanmar_all_12m", "en"),
    "S6": ("burkina_all_3m", "en"),
}
TYPES = {"situation": 12, "needs_assessment": 12, "indicator_monitoring": 16}

# The headings each prompt requires (rag/chain.py), in English; a Turkish report
# translates them, so `check` only counts level-2 headings there.
REQUIRED = {
    "situation": ["Executive Summary"],
    "indicator_monitoring": ["Overview", "Indicator Table"],
    "needs_assessment": ["Context"],
}


def _read_only_db():
    """Point rag.retriever at a read-only connection of this script's own."""
    from dotenv import load_dotenv
    from sqlalchemy import create_engine, text
    import rag.retriever as retriever

    load_dotenv(".env")
    url = re.sub(r"^postgres(ql)?://", "postgresql+psycopg://", os.environ["DATABASE_URL"])
    engine = create_engine(url, pool_pre_ping=True)

    @contextmanager
    def connect():
        with engine.connect() as conn:
            conn.execute(text("SET TRANSACTION READ ONLY"))
            yield conn
            conn.rollback()

    retriever.connect = connect


def _doc_to_json(doc) -> dict:
    meta = {k: v for k, v in doc.metadata.items() if not k.startswith("_")}
    meta["_relevance_score"] = doc.metadata.get("_relevance_score")
    return {"page_content": doc.page_content, "metadata": meta}


def _json_to_doc(d: dict):
    from langchain_core.documents import Document
    return Document(page_content=d["page_content"], metadata=d["metadata"])


def packets(force: bool) -> None:
    from datetime import date, timedelta
    from rag.report_service import retrieve_for_report

    _read_only_db()
    out = OUT / "packets"
    out.mkdir(parents=True, exist_ok=True)
    for pid, spec in PACKETS.items():
        path = out / f"{pid}.json"
        if path.exists() and not force:
            print(f"{pid}: kept (exists)")
            continue
        date_to = date.today().isoformat()
        date_from = (date.today() - timedelta(days=spec["days"])).isoformat()
        docs = asyncio.run(retrieve_for_report(spec["country"], spec["theme"], date_from, date_to,
                                               top_k=16, report_type="indicator_monitoring"))
        reranked = sum(1 for d in docs if d.metadata.get("_relevance_score") is not None)
        path.write_text(json.dumps({
            **spec, "date_from": date_from, "date_to": date_to,
            "reranked": reranked, "docs": [_doc_to_json(d) for d in docs],
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{pid}: {len(docs)} documents, {reranked} with a rerank score")
        if docs and not reranked:
            print("  WARNING: no rerank scores (quota?): this packet is not production-like")


def generate(only: list[str], force: bool) -> None:
    from rag.rag_context import _build_context_and_sources
    from rag.chain import build_report_chain
    from rag.citations import normalize_citations, normalize_table_delimiters
    from rag.report_service import build_report_directive

    out = OUT / "reports"
    out.mkdir(parents=True, exist_ok=True)
    for sid, (pid, lang) in SCENARIOS.items():
        if only and sid not in only:
            continue
        packet = json.loads((OUT / "packets" / f"{pid}.json").read_text(encoding="utf-8"))
        for rtype, k in TYPES.items():
            path = out / f"{sid}_{rtype}.json"
            if path.exists() and not force:
                print(f"{sid} {rtype}: kept (exists)")
                continue
            docs = [_json_to_doc(d) for d in packet["docs"][:k]]
            context, source_dicts = _build_context_and_sources(docs)
            directive = build_report_directive(
                packet["country"], packet["theme"], packet["date_from"], packet["date_to"],
                len(docs), lang, report_type=rtype)
            t0 = time.perf_counter()
            try:
                raw = build_report_chain(rtype).invoke({"question": directive, "context": context})
                error = None
            except Exception as exc:
                raw, error = "", repr(exc)[:300]
            seconds = round(time.perf_counter() - t0, 1)
            clean, sources = normalize_citations(
                raw, source_dicts, keep_uncited=rtype == "indicator_monitoring")
            clean = normalize_table_delimiters(clean)
            path.write_text(json.dumps({
                "scenario": sid, "packet": pid, "language": lang, "type": rtype,
                "docs_in_context": len(docs), "seconds": seconds, "error": error,
                "raw": raw, "content": clean, "sources": sources, "context_sources": source_dicts,
            }, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"{sid} {rtype}: {seconds}s, {len(clean)} chars, {len(sources)} sources"
                  + (f", ERROR {error}" if error else ""))


_CITE = re.compile(r"\[\d+(?:\s*[,–-]\s*\d+)*\]")


def check() -> None:
    rows = []
    for path in sorted((OUT / "reports").glob("*.json")):
        r = json.loads(path.read_text(encoding="utf-8"))
        content = r["content"]
        headings = re.findall(r"(?m)^##\s+(.+)$", content)
        paragraphs = [p for p in re.split(r"\n\s*\n", content)
                      if p.strip() and not p.lstrip().startswith(("#", "|"))]
        table_rows = [ln for ln in content.splitlines()
                      if ln.startswith("|") and not re.match(r"^\|[\s:|-]+\|?$", ln)][1:]
        cited_raw = set(int(n) for n in re.findall(r"\[(\d+)", r["raw"]))
        missing = ([h for h in REQUIRED[r["type"]] if not any(h.lower() in x.lower() for x in headings)]
                   if r["language"] == "en" else [])
        rows.append({
            "report": path.stem, "seconds": r["seconds"], "error": r["error"],
            "chars": len(content), "headings": len(headings), "missing_headings": missing,
            "sources_shown": len(r["sources"]), "context_docs": r["docs_in_context"],
            "context_docs_cited_in_raw": len(cited_raw),
            "paragraphs_without_citation": sum(1 for p in paragraphs if not _CITE.search(p)),
            "paragraphs": len(paragraphs),
            "table_rows_without_citation": sum(1 for t in table_rows if not _CITE.search(t)),
            "table_rows": len(table_rows),
        })
    (OUT / "check.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    for row in rows:
        print(row)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=["packets", "generate", "check"])
    parser.add_argument("--only", nargs="*", default=[], help="scenario ids for generate (S1 ...)")
    parser.add_argument("--force", action="store_true", help="redo files that exist")
    args = parser.parse_args()
    if args.step == "packets":
        packets(args.force)
    elif args.step == "generate":
        generate(args.only, args.force)
    else:
        check()


if __name__ == "__main__":
    main()
