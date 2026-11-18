"""Generate a sample chat answer the landing page quotes.

Runs the chat pipeline's own pieces once, as the first message of a new conversation
(no history): rag.query_processor filter extraction, the chat route's retrieval
(api.routes.chat._retrieve_docs) and rag.chain's chat chain. Writes
frontend/src/marketing/data/syriaAnswer.<lang>.json: the question, the answer verbatim
as parts (text / strong / cite), the sources it cites and the generation date.

Safety: the database is only read. rag.db.get_engine() would run its schema setup
(ALTER/CREATE/REVOKE) on first use, so use_read_only_db() installs a read-only engine
with no schema setup before anything connects; any write would fail. Nothing is saved
(no conversation, no message, no report); the full answer goes to a local file (--raw).
The chat model is called once, with no retry. The reranker is switched off (its monthly
quota is shared with the live app), so ranking falls back to the MMR/recency order, as
it does when the quota is spent.

When to regenerate: rarely, when the quoted sample should change. A normal run COSTS A
GEMINI CALL (one answer, plus the query processor's filter call and the query
embedding); --dry-run stops before the answer (prints the filters and retrieved
sources); --reuse re-parses a saved --raw file and costs nothing. Review and commit
the file it writes.

Usage:
    python scripts/generate_landing_answer.py --lang en --question "<text>" --raw <path.json>
    python scripts/generate_landing_answer.py --lang en --question "<text>" --raw <p> --dry-run
    python scripts/generate_landing_answer.py --lang en --raw <path.json> --reuse
"""
import argparse
import asyncio
import json
import logging
import os
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)

OUT_DIR = ROOT / "frontend" / "src" / "marketing" / "data"
LANGUAGES = {"en": "English", "tr": "Turkish"}
MIN_CITED_SOURCES = 3

# **bold** | [n] / [n, m] | a list marker ("* ", "- ", "1. ") at the start of a line.
_TOKEN = re.compile(r"\*\*(.+?)\*\*|\[(\d+(?:\s*,\s*\d+)*)\]|^([ \t]*(?:[*-]|\d+\.)[ \t]+)",
                    re.DOTALL | re.MULTILINE)
_CITE = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")


def use_read_only_db() -> None:
    """Point rag.db at a read-only engine for DATABASE_URL, without schema setup.

    rag.db.get_engine() runs _ensure_schema (ALTER TABLE ... ADD COLUMN, CREATE ... IF
    NOT EXISTS, ENABLE ROW LEVEL SECURITY, REVOKE) the first time it opens an engine;
    on the live database that would change production. These scripts only read, so
    the schema setup is replaced with a no-op and the engine get_engine() hands out is
    pre-registered with every Postgres transaction read-only. Call before any import
    that connects."""
    from sqlalchemy import create_engine

    import rag.db as db

    db._ensure_schema = lambda engine: None
    url = db._db_url()
    engine = create_engine(url, pool_pre_ping=True)
    if engine.dialect.name == "postgresql":
        engine = engine.execution_options(postgresql_readonly=True)
    db._engines[url] = engine


def parse_answer(text: str, sources: list[dict]) -> dict:
    """Split an answer into the landing's parts: plain text, **bold** as strong text,
    [n] / [n, m] markers as cite parts (the space before a marker goes, since the page
    draws the marker itself; a number no source carries is dropped), and a list marker
    at the start of a line ("* ", "- ", "1. ") as its own text part flagged
    list_item: true, so the page can draw a list. The text itself is kept verbatim
    (markers included). Sources are the cited ones, in number order."""
    by_n = {s["index"]: s for s in sources if s.get("index") is not None}
    parts: list[dict] = []

    def add_text(t: str, strong: bool = False) -> None:
        if not t:
            return
        last = parts[-1] if parts else None
        if (last and "text" in last and not last.get("list_item")
                and last.get("strong", False) == strong):
            last["text"] += t
        else:
            parts.append({"text": t, "strong": True} if strong else {"text": t})

    def add_cites(group: str) -> None:
        if parts and "text" in parts[-1] and not parts[-1].get("list_item"):
            parts[-1]["text"] = parts[-1]["text"].rstrip(" ")
            if not parts[-1]["text"]:
                parts.pop()
        parts.extend({"cite": n} for n in (int(x) for x in group.split(",")) if n in by_n)

    def add_strong(t: str) -> None:
        pos = 0
        for m in _CITE.finditer(t):
            add_text(t[pos:m.start()], strong=True)
            add_cites(m.group(1))
            pos = m.end()
        add_text(t[pos:], strong=True)

    pos = 0
    for m in _TOKEN.finditer(text):
        add_text(text[pos:m.start()])
        if m.group(1) is not None:
            add_strong(m.group(1))
        elif m.group(2) is not None:
            add_cites(m.group(2))
        else:
            parts.append({"text": m.group(3), "list_item": True})
        pos = m.end()
    add_text(text[pos:])

    cited = sorted({p["cite"] for p in parts if "cite" in p})
    return {
        "parts": parts,
        "sources": [{"n": n, "title": by_n[n]["title"],
                     "meta": " · ".join(x for x in (by_n[n].get("source"), by_n[n].get("country")) if x),
                     "date": by_n[n].get("date"), "url": by_n[n]["url"]} for n in cited],
    }


async def _generate(question: str, lang: str, dry_run: bool) -> dict | None:
    from api.routes.chat import _drop_unknown_country, _retrieve_docs
    from rag.chain import answer_language, build_chain, describe_filters
    from rag.query_processor import extract_filters
    from rag.rag_context import _build_context_and_sources

    # The chat route picks the answer language from the question; check it before
    # any paid call.
    language = answer_language(question, [])
    if language != LANGUAGES[lang]:
        raise SystemExit(f"The question reads as {language!r}, not {LANGUAGES[lang]}; nothing generated.")

    # A first message: the route's _plan_retrieval is the message plus extract_filters.
    filters = _drop_unknown_country(extract_filters(question))
    docs = await _retrieve_docs(question, filters)
    if not docs:
        raise SystemExit(f"No documents retrieved (filters {filters}); nothing generated.")
    context, source_dicts = _build_context_and_sources(docs)
    logger.info("Filters: %s", filters)
    for s in source_dicts:
        logger.info("[%d] %s | %s | %s", s["index"], s.get("date"), s.get("source"), s["title"])
    if dry_run:
        return None

    answer = await build_chain().ainvoke({   # max_retries=0: one model call
        "question": question,
        "context": context,
        "chat_history": [],
        "answer_language": language,
        "applied_filters": describe_filters(filters),
    })
    return {"generated": date.today().isoformat(), "lang": lang, "question": question,
            "filters": filters, "answer": answer, "sources": source_dicts}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lang", choices=sorted(LANGUAGES), required=True)
    parser.add_argument("--question", help="the question, in --lang (not needed with --reuse)")
    parser.add_argument("--raw", type=Path, required=True,
                        help="local file for the full generated answer (never committed)")
    parser.add_argument("--reuse", action="store_true",
                        help="re-parse an existing --raw file without calling the model")
    parser.add_argument("--dry-run", action="store_true",
                        help="stop after retrieval (no answer generated, nothing written)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.reuse:
        raw = json.loads(args.raw.read_text(encoding="utf-8"))
    else:
        if not args.question:
            parser.error("--question is required unless --reuse")
        os.environ["RERANK_ENABLED"] = "false"
        from config import get_settings
        get_settings.cache_clear()
        use_read_only_db()
        raw = asyncio.run(_generate(args.question, args.lang, args.dry_run))
        if raw is None:
            return
        args.raw.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
        logger.info("Generated with one model call; full answer at %s", args.raw)

    parsed = parse_answer(raw["answer"], raw["sources"])
    if len(parsed["sources"]) < MIN_CITED_SOURCES:
        raise SystemExit(f"The answer cites {len(parsed['sources'])} source(s), fewer than "
                         f"{MIN_CITED_SOURCES}; sample not written.")
    out = {"question": raw["question"], **parsed, "generated": raw["generated"]}
    path = OUT_DIR / f"syriaAnswer.{raw['lang']}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    logger.info("Wrote %s", path)


if __name__ == "__main__":
    main()
