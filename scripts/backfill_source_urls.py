"""One-off backfill: fix broken source-link URLs in the Pinecone index.

Historical ingests stored the displayed source link as the synthesized
``https://reliefweb.int/report/{numeric-id}`` path, which 404s on ReliefWeb
(the site serves reports at ``/node/{id}`` or the ``/report/{slug}`` alias).
This script rewrites only the ``url`` metadata field of affected vectors to
``https://reliefweb.int/node/{id}`` (which redirects to the live page). No
re-embedding happens — values are untouched, only metadata is updated.

The parser fix (ingestion/parser.py) handles NEW ingests; this repairs the
data that was already written.

Usage:
    python scripts/backfill_source_urls.py            # dry-run (read-only)
    python scripts/backfill_source_urls.py --apply    # perform the update
    python scripts/backfill_source_urls.py --apply --workers 24
"""

import argparse
import logging
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pinecone import Pinecone

from config import get_settings

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Only the synthesized /report/{numeric-id} path is broken. A real alias such
# as /report/ukraine/snapshot has extra path segments and is left untouched.
# fetch() puts ids in the request URI, so keep batches small to stay under the
# server's URI length limit (1000 ids -> HTTP 414).
_BROKEN = re.compile(r"^https://reliefweb\.int/report/(\d+)$")
_FETCH_BATCH = 50


def _collect_ids(index, namespace):
    ids = []
    for page in index.list(namespace=namespace):
        ids.extend(page)
        if len(ids) % 5000 < len(page):
            logger.info("  collected %d ids...", len(ids))
    return ids


def _find_broken(index, namespace, ids):
    """Return {vector_id: new_url} for vectors whose url needs fixing."""
    to_fix = {}
    for i in range(0, len(ids), _FETCH_BATCH):
        batch = ids[i : i + _FETCH_BATCH]
        vectors = index.fetch(ids=batch, namespace=namespace).vectors
        for vid, vec in vectors.items():
            url = (vec.metadata or {}).get("url", "")
            m = _BROKEN.match(url)
            if m:
                to_fix[vid] = f"https://reliefweb.int/node/{m.group(1)}"
        if (i // _FETCH_BATCH) % 100 == 0:
            logger.info("  scanned %d/%d vectors, %d broken so far...", min(i + _FETCH_BATCH, len(ids)), len(ids), len(to_fix))
    return to_fix


def _apply(index, namespace, to_fix, workers):
    def update_one(item):
        vid, new_url = item
        index.update(id=vid, set_metadata={"url": new_url}, namespace=namespace)

    done = 0
    failed = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(update_one, it): it[0] for it in to_fix.items()}
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception as e:  # noqa: BLE001 — collect and report, keep going
                failed.append((futures[fut], str(e)))
            done += 1
            if done % 1000 == 0:
                logger.info("  updated %d/%d", done, len(to_fix))
    return done, failed


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="perform updates (default: dry-run)")
    ap.add_argument("--workers", type=int, default=16, help="concurrent update workers")
    args = ap.parse_args()

    settings = get_settings()
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    index = pc.Index(settings.PINECONE_INDEX)
    namespace = settings.PINECONE_NAMESPACE or None

    logger.info("Index: %s | namespace: %s", settings.PINECONE_INDEX, namespace)
    ids = _collect_ids(index, namespace)
    logger.info("Total vectors: %d", len(ids))

    to_fix = _find_broken(index, namespace, ids)
    logger.info("Broken /report/{id} urls: %d", len(to_fix))
    for vid, new_url in list(to_fix.items())[:3]:
        logger.info("  sample: %s -> %s", vid, new_url)

    if not to_fix:
        logger.info("Nothing to fix.")
        return
    if not args.apply:
        logger.info("DRY-RUN — re-run with --apply to write %d updates.", len(to_fix))
        return

    logger.info("Applying %d metadata updates (workers=%d)...", len(to_fix), args.workers)
    done, failed = _apply(index, namespace, to_fix, args.workers)
    logger.info("Updated %d vectors. Failed: %d", done - len(failed), len(failed))
    if failed:
        for vid, err in failed[:10]:
            logger.warning("  FAILED %s: %s", vid, err)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
