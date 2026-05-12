import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from ingestion.client import ReliefWebClient, ENDPOINT_CONFIG
from ingestion.parser import parse
from ingestion.chunker import chunk_document
from ingestion.embedder import OllamaEmbedder
from ingestion.store import ChromaStore

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


@dataclass
class IngestionStats:
    endpoint: str
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list = field(default_factory=list)


def run_pipeline(
    limit: int = 1000,
    force: bool = False,
    endpoints: Optional[List[str]] = None,
    date_from: Optional[str] = None,
) -> Dict[str, IngestionStats]:
    if endpoints is None:
        endpoints = ["reports"]
    logger.info("Starting ingestion pipeline (limit=%d, force=%s, endpoints=%s, date_from=%s)", limit, force, endpoints, date_from)
    client = ReliefWebClient()
    embedder = OllamaEmbedder()
    store = ChromaStore()
    if force:
        store.clear_collection()
    all_stats: Dict[str, IngestionStats] = {}
    for endpoint in endpoints:
        stats = IngestionStats(endpoint=endpoint)
        offset = 0
        logger.info("Ingesting endpoint '%s' (limit=%d)", endpoint, limit)
        processed = 0
        start_time = time.time()
        while processed < limit:
            batch_limit = min(BATCH_SIZE, limit - processed)
            items = client.fetch(endpoint, limit=batch_limit, offset=offset, date_from=date_from)
            if not items:
                break
            for raw in items:
                stats.total += 1
                processed += 1
                try:
                    doc = parse(raw, endpoint)
                    if not doc or not doc.get("body"):
                        stats.skipped += 1
                        continue
                    chunks = chunk_document(doc)
                    if not chunks:
                        stats.skipped += 1
                        continue
                    texts = [c["content"] for c in chunks]
                    embeddings = embedder.embed_batch(texts)
                    store.upsert_chunks(chunks, embeddings)
                    stats.succeeded += 1
                except Exception as e:
                    stats.failed += 1
                    url = raw.get("fields", {}).get("url", "unknown") if isinstance(raw.get("fields"), dict) else "unknown"
                    if len(stats.errors) < 10:
                        stats.errors.append({"url": url, "error": str(e)})
                    logger.warning("Failed to process doc from %s: %s", endpoint, e)
                    continue
            offset += batch_limit
            elapsed = time.time() - start_time
            rate = stats.succeeded / elapsed if elapsed > 0 else 0
            eta_min = (limit - processed) / rate / 60 if rate > 0 else 0
            logger.info(
                "%s: %d/%d processed (%d OK, %d failed, %d skipped) — %.1f docs/sec, ETA %.0f min",
                endpoint, processed, limit, stats.succeeded, stats.failed, stats.skipped,
                rate, eta_min,
            )
        logger.info(
            "Endpoint '%s' complete: %d succeeded, %d failed, %d skipped",
            endpoint, stats.succeeded, stats.failed, stats.skipped,
        )
        all_stats[endpoint] = stats
    logger.info("Ingestion pipeline complete.")
    return all_stats