"""Ranking metrics for retrieval evaluation (binary relevance).

Each function takes the retriever's ranked list of doc ids and the set of
ground-truth relevant doc ids for a query. Aggregation (e.g. mean over queries
for MRR) is done by the caller.
"""
import math


def recall_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Fraction of the relevant docs that appear in the top-k. 0 if no labels."""
    if not relevant_ids:
        return 0.0
    top_k = ranked_ids[:k]
    hits = sum(1 for doc_id in relevant_ids if doc_id in top_k)
    return hits / len(relevant_ids)


def reciprocal_rank(ranked_ids: list[str], relevant_ids: set[str]) -> float:
    """1 / rank of the first relevant doc (1-based), or 0 if none retrieved."""
    for i, doc_id in enumerate(ranked_ids, start=1):
        if doc_id in relevant_ids:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Normalised DCG@k with binary gains (relevant=1)."""
    if not relevant_ids:
        return 0.0
    dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank, doc_id in enumerate(ranked_ids[:k], start=1)
        if doc_id in relevant_ids
    )
    ideal_hits = min(len(relevant_ids), k)
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / idcg if idcg else 0.0
