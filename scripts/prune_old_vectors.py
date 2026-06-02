"""Prune old vectors from the Pinecone index (keep recent humanitarian data).

A country ingestion run without --date-from (e.g. --country IRN) pulled ReliefWeb's
full country history back to the 1990s. For a current-situation M&E tool, decades-old
reports are low-value and add noise to unfiltered queries. This deletes chunks whose
date_ts is a REAL date older than the cutoff. Documents with date_ts == 0
(unparseable/missing date) are NOT touched.

Pinecone serverless has no metadata-filtered delete, so we collect matching chunk IDs
(one filtered query) and delete them by ID in batches.

Usage:
    python scripts/prune_old_vectors.py                          # dry-run, cutoff 2023-01-01
    python scripts/prune_old_vectors.py --before 2023-01-01      # dry-run with cutoff
    python scripts/prune_old_vectors.py --before 2023-01-01 --apply
"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pinecone import Pinecone

from config import get_settings

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

_QUERY_TOP_K = 10000   # Pinecone query cap; we abort if matches hit this (would be incomplete)
_DELETE_BATCH = 1000   # Pinecone delete-by-id batch limit
_MIN_TS = 19000101     # floor so date_ts == 0 (missing/unparseable date) is never matched


def _date_to_ts(d: str) -> int:
    """'2023-01-01' -> 20230101."""
    return int(d.replace("-", ""))


def _batched(items, size):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _query_old(index, namespace, vec, hi_ts, top_k, include_metadata):
    return index.query(
        vector=vec, top_k=top_k, include_metadata=include_metadata, namespace=namespace,
        filter={"date_ts": {"$gte": _MIN_TS, "$lt": hi_ts}},
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--before", default="2023-01-01", help="delete docs dated before this (YYYY-MM-DD)")
    ap.add_argument("--apply", action="store_true", help="perform deletion (default: dry-run)")
    args = ap.parse_args()

    s = get_settings()
    pc = Pinecone(api_key=s.PINECONE_API_KEY)
    index = pc.Index(s.PINECONE_INDEX)
    namespace = s.PINECONE_NAMESPACE or None
    vec = [0.1] * s.EMBED_DIM
    hi_ts = _date_to_ts(args.before)

    total = index.describe_index_stats().get("total_vector_count")
    matches = _query_old(index, namespace, vec, hi_ts, _QUERY_TOP_K, False).get("matches", [])
    if len(matches) >= _QUERY_TOP_K:
        logger.error("Matched %d chunks (>= top_k cap %d) — collection would be INCOMPLETE; "
                     "aborting. Use a more recent --before, or extend the script to paginate via index.list().",
                     len(matches), _QUERY_TOP_K)
        raise SystemExit(2)

    ids = [m["id"] for m in matches]
    doc_ids = {i.rsplit("_", 1)[0] for i in ids}
    logger.info("Index: %s | namespace: %s | total vectors: %s", s.PINECONE_INDEX, namespace, total)
    logger.info("Cutoff: date < %s  (ts < %d; date_ts=0/missing-date docs EXCLUDED)", args.before, hi_ts)
    logger.info("To delete: %d chunks across %d documents.", len(ids), len(doc_ids))

    sample = _query_old(index, namespace, vec, hi_ts, 15, True).get("matches", [])
    logger.info("Sample of documents that would be deleted:")
    seen = set()
    for m in sample:
        md = m.get("metadata", {})
        did = m["id"].rsplit("_", 1)[0]
        if did in seen:
            continue
        seen.add(did)
        logger.info("  %s | %s | %s", md.get("date"), md.get("country"), (md.get("title") or "")[:55])

    if not args.apply:
        logger.info("DRY-RUN — re-run with --apply to delete these %d chunks.", len(ids))
        return

    logger.info("Deleting %d chunks in batches of %d...", len(ids), _DELETE_BATCH)
    deleted = 0
    for batch in _batched(ids, _DELETE_BATCH):
        index.delete(ids=batch, namespace=namespace)
        deleted += len(batch)
        logger.info("  deleted %d/%d", deleted, len(ids))

    remaining = _query_old(index, namespace, vec, hi_ts, _QUERY_TOP_K, False).get("matches", [])
    logger.info("Done. Deleted %d chunks. Old chunks still matching (eventual consistency): %d", deleted, len(remaining))


if __name__ == "__main__":
    main()
