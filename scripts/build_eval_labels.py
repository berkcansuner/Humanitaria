"""Build the labeled retrieval eval set (silver labels via pooled LLM judgment).

For each query we pool candidate documents from the live pgvector corpus — the
dense top chunks under the query's extracted filters (the pool the chat pipeline
reranks from) plus the unfiltered dense top chunks — dedupe by canonical doc_id,
and ask an LLM which candidates are relevant (TREC-style pooling).

The corpus is a rolling one-year window refreshed nightly, so labels go stale:
rebuild the set at the start of each eval session (scripts/eval_rag.py --metrics
warns when labeled documents have left the corpus).

Each entry also stores the query's extracted filters, so eval runs can reuse them
and compare retrieval changes without the filter LLM's run-to-run variance.

Read-only against the database. Gemini cost: one embedding per query (x2 searches)
+ one filter extraction + 1-2 judge calls (gemini query model).

Usage:
    python scripts/build_eval_labels.py
    python scripts/build_eval_labels.py --pool-k 60 --open-k 30
Output: scripts/eval_data/labeled_queries.json
"""
import argparse
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from config import get_settings

QUERIES = [
    "Sudan'daki güncel insani durum",
    "food security in Yemen",
    "Suriye'de sağlık hizmetleri",
    "Afghanistan displacement situation",
    "Somali'de gıda krizi",
    "earthquake recovery in Türkiye",
    "Irak'ta yerinden edilmiş kişiler",
    "Yemen'de çocuk beslenmesi",
    "protection concerns in Sudan",
    "Suriye'de barınma ihtiyaçları",
    "health needs in Afghanistan",
    "Somalia drought impact",
    "Sudan'da gıda güvenliği",
    "water and sanitation in Yemen",
    "humanitarian access in Syria",
    "humanitarian situation in Haiti",
    "Kongo Demokratik Cumhuriyeti'nde kolera salgını",
    "Ethiopia drought and food insecurity",
    "Ukrayna'da sivillerin korunması",
    "displacement in Myanmar",
    "Venezuelan migrants and refugees",
    "flooding response in Pakistan",
    "Bangladeş'te Rohingya mültecilerinin durumu",
    "cholera outbreak in South Sudan",
    "Mali'de insani erişim",
    # historical / trend intent (the pipeline turns the recency boost off for these)
    "How has the cholera situation in Sudan evolved over time?",
    "Yemen'de gıda güvensizliği yıllar içinde nasıl değişti",
    "displacement trend in the Democratic Republic of the Congo",
    # several countries in one question
    "Sudan ve Çad'daki mülteci durumu",
    "cholera in Sudan and South Sudan",
]

OUTPUT = Path(__file__).resolve().parent / "eval_data" / "labeled_queries.json"
_JUDGE_BATCH = 30   # candidates per judge call (long listings blur the judge's attention)

_JUDGE_PROMPT = (
    "You label which candidate documents are RELEVANT to a humanitarian query.\n"
    "Be STRICT: mark a document relevant ONLY if it directly and substantially "
    "addresses BOTH the query's country (any of them, when it names several) AND its specific topic. Exclude candidates that "
    "are only loosely related (right country, wrong topic — or vice versa). Ignore how "
    "recent a document is; judge topical relevance only.\n"
    "Return ONLY a JSON array of the indices of the relevant candidates, e.g. [0, 2, 5]. "
    "If none are relevant, return [].\n\n"
    "QUERY:\n{query}\n\nCANDIDATES:\n{candidates}\n"
)


def parse_indices(text: str) -> list[int]:
    """Parse a bare JSON array of ints; tolerate prose or a code fence around it."""
    try:
        data = json.loads(text)
    except Exception:
        m = re.search(r"\[[\d,\s]*\]", text or "")
        data = json.loads(m.group(0)) if m else []
    if not isinstance(data, list):
        return []
    return [int(x) for x in data if isinstance(x, (int, float))]


def pool_candidates(doc_lists) -> list[dict]:
    """Union of several ranked chunk lists, one entry per doc_id (first seen wins)."""
    seen, pool = set(), []
    for docs in doc_lists:
        for doc in docs:
            doc_id = doc.metadata.get("doc_id")
            if not doc_id or doc_id in seen:
                continue
            seen.add(doc_id)
            pool.append({
                "doc_id": doc_id,
                "title": doc.metadata.get("title", "Untitled"),
                "date": doc.metadata.get("date") or "",
                "snippet": (doc.page_content or "")[:500].replace("\n", " "),
            })
    return pool


def get_judge():
    from langchain_openai import ChatOpenAI
    s = get_settings()
    return ChatOpenAI(model=s.GEMINI_QUERY_MODEL, base_url=s.GEMINI_BASE_URL,
                      api_key=s.GEMINI_API_KEY, use_responses_api=False,
                      temperature=0.0, timeout=60, max_retries=0)


def judge_relevant(judge, query: str, batch: list[dict], retries: int = 4) -> list[int]:
    """Indices (into *batch*) the judge marks relevant; retries transient errors."""
    listing = "\n".join(f"[{i}] {c['title']} ({c['date']}) — {c['snippet']}" for i, c in enumerate(batch))
    prompt = _JUDGE_PROMPT.format(query=query, candidates=listing)
    for attempt in range(retries):
        try:
            resp = judge.invoke(prompt)
            return [i for i in parse_indices(getattr(resp, "content", str(resp))) if 0 <= i < len(batch)]
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    return []


def main():
    from rag.query_processor import extract_filters
    from rag.retriever import search

    ap = argparse.ArgumentParser()
    ap.add_argument("--pool-k", type=int, default=60,
                    help="Dense chunks fetched under the query's filters (the chat pipeline's pool is 60)")
    ap.add_argument("--open-k", type=int, default=30, help="Dense chunks fetched without filters")
    args = ap.parse_args()

    judge = get_judge()
    print(f"Building labels from pgvector (pool-k={args.pool_k}, open-k={args.open_k})\n" + "=" * 70)

    dataset = []
    for query in QUERIES:
        filters = extract_filters(query)
        # search() with k == fetch_k keeps every fetched chunk (MMR only reorders).
        filtered = search(query, filters or None, args.pool_k, args.pool_k)
        unfiltered = search(query, None, args.open_k, args.open_k)
        pool = pool_candidates([filtered, unfiltered])
        if not pool:
            print(f"[skip] no candidates: {query}")
            continue
        relevant = []
        try:
            for start in range(0, len(pool), _JUDGE_BATCH):
                batch = pool[start:start + _JUDGE_BATCH]
                relevant += [batch[i]["doc_id"] for i in judge_relevant(judge, query, batch)]
        except Exception as e:
            print(f"[warn] judge failed for {query!r}: {e}")
            relevant = []
        dataset.append({
            "query": query,
            "filters": filters,
            "relevant_doc_ids": relevant,
            "judged_doc_ids": [c["doc_id"] for c in pool],
            "n_candidates": len(pool),
            "n_relevant": len(relevant),
        })
        print(f"[ok] {query}  ->  {len(relevant)}/{len(pool)} relevant  filters={filters}")

    payload = {"built": date.today().isoformat(), "queries": dataset}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    labeled = sum(1 for d in dataset if d["n_relevant"] > 0)
    print("=" * 70)
    print(f"Wrote {len(dataset)} queries ({labeled} with ≥1 relevant) -> {OUTPUT}")


if __name__ == "__main__":
    main()
