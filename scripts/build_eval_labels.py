"""Build a labeled retrieval eval set (silver labels via pooled LLM judgment).

For each query we pool candidate documents from BOTH namespaces being compared
(default + v2), dedupe by canonical doc_id, then ask an LLM which candidates are
relevant. The resulting {query -> relevant doc_ids} set is namespace-independent
(doc_id is the canonical report id), so the same gold set scores both namespaces
fairly — the standard TREC pooling approach.

Queries stay within v2's country coverage (the 8 re-ingested countries) so the
comparison reflects CHUNKING quality, not coverage differences.

Read-only (no Pinecone writes) → safe under the monthly write-unit quota.

Usage:
    python scripts/build_eval_labels.py
    python scripts/build_eval_labels.py --namespaces "" v2 --pool-k 8
Output: scripts/eval_data/labeled_queries.json
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

from config import get_settings
from rag.embeddings import get_embeddings

# Queries within v2's 8-country coverage (IRN/IRQ/SYR/TUR/YEM/AFG/SOM/SDN), TR+EN.
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
]

OUTPUT = Path(__file__).resolve().parent / "eval_data" / "labeled_queries.json"


_JUDGE_PROMPT = (
    "You label which candidate documents are RELEVANT to a humanitarian query.\n"
    "Be STRICT: mark a document relevant ONLY if it directly and substantially "
    "addresses BOTH the query's country AND its specific topic. Many candidates are "
    "only loosely related (right country, wrong topic — or vice versa); exclude those. "
    "Typically only 2-6 candidates are truly relevant.\n"
    "Return ONLY a JSON array of the indices of the relevant candidates, e.g. [0, 2, 5]. "
    "If none are relevant, return [].\n\n"
    "QUERY:\n{query}\n\nCANDIDATES:\n{candidates}\n"
)


def _parse_indices(text: str) -> list[int]:
    """Parse a bare JSON array of ints; tolerate extra prose around it."""
    try:
        data = json.loads(text)
    except Exception:
        m = re.search(r"\[[\d,\s]*\]", text or "")
        data = json.loads(m.group(0)) if m else []
    return [int(x) for x in data if isinstance(x, (int, float))]


def _vectorstore(namespace: str):
    settings = get_settings()
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    index = pc.Index(settings.PINECONE_INDEX)
    return PineconeVectorStore(
        index=index, embedding=get_embeddings(), text_key="text",
        namespace=namespace or None,
    )


def _get_judge():
    from langchain_openai import ChatOpenAI
    s = get_settings()
    return ChatOpenAI(model=s.GEMINI_QUERY_MODEL, base_url=s.GEMINI_BASE_URL,
                      api_key=s.GEMINI_API_KEY, temperature=0.0, timeout=40)


def _judge_relevant(judge, query: str, listing: str, retries: int = 4) -> list[int]:
    """Invoke the judge with retry on transient errors (e.g. 503 high demand)."""
    prompt = _JUDGE_PROMPT.format(query=query, candidates=listing)
    for attempt in range(retries):
        try:
            resp = judge.invoke(prompt)
            return _parse_indices(getattr(resp, "content", str(resp)))
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    return []


def _pool_candidates(query: str, stores, pool_k: int) -> list[dict]:
    """Union top-k from each namespace, deduped by doc_id."""
    seen, pool = set(), []
    for store in stores:
        for doc in store.similarity_search(query, k=pool_k):
            doc_id = doc.metadata.get("doc_id")
            if not doc_id or doc_id in seen:
                continue
            seen.add(doc_id)
            pool.append({
                "doc_id": doc_id,
                "title": doc.metadata.get("title", "Untitled"),
                "snippet": (doc.page_content or "")[:300].replace("\n", " "),
            })
    return pool


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--namespaces", nargs="+", default=["", "v2"],
                    help="Namespaces to pool candidates from (default: '' and v2)")
    ap.add_argument("--pool-k", type=int, default=8, help="Candidates per namespace per query")
    args = ap.parse_args()

    stores = [_vectorstore(ns) for ns in args.namespaces]
    judge = _get_judge()
    print(f"Building labels from namespaces {args.namespaces} (pool-k={args.pool_k})\n" + "=" * 70)

    dataset = []
    for query in QUERIES:
        pool = _pool_candidates(query, stores, args.pool_k)
        if not pool:
            print(f"[skip] no candidates: {query}")
            continue
        listing = "\n".join(f"[{i}] {c['title']} — {c['snippet']}" for i, c in enumerate(pool))
        try:
            raw = _judge_relevant(judge, query, listing)
            rel_idx = [i for i in raw if 0 <= i < len(pool)]
        except Exception as e:
            print(f"[warn] judge failed for {query!r}: {e}")
            rel_idx = []
        relevant_ids = [pool[i]["doc_id"] for i in rel_idx]
        dataset.append({
            "query": query,
            "relevant_doc_ids": relevant_ids,
            "n_candidates": len(pool),
            "n_relevant": len(relevant_ids),
        })
        print(f"[ok] {query}  ->  {len(relevant_ids)}/{len(pool)} relevant")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
    labeled = sum(1 for d in dataset if d["n_relevant"] > 0)
    print("=" * 70)
    print(f"Wrote {len(dataset)} queries ({labeled} with ≥1 relevant) -> {OUTPUT}")


if __name__ == "__main__":
    main()
