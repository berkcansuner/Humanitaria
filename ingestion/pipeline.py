import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Any

from config import get_settings
from ingestion.client import ReliefWebClient, ENDPOINT_CONFIG
from ingestion.parser import parse
from ingestion.chunker import chunk_document
from ingestion.store import get_store
from rag.embeddings import get_embeddings

logger = logging.getLogger(__name__)

BATCH_SIZE = 500  # max documents per ReliefWeb API fetch


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
    country: Optional[str] = None,
) -> Dict[str, IngestionStats]:
    if endpoints is None:
        endpoints = ["reports"]
    settings = get_settings()
    logger.info(
        "Starting ingestion pipeline (limit=%d, force=%s, endpoints=%s, date_from=%s, country=%s)",
        limit, force, endpoints, date_from, country,
    )
    client = ReliefWebClient()
    embedder = get_embeddings()
    store = get_store()

    if force:
        store.clear_collection()

    all_stats: Dict[str, IngestionStats] = {}

    for endpoint in endpoints:
        stats = IngestionStats(endpoint=endpoint)
        offset = 0
        processed = 0
        start_time = time.time()
        logger.info("Ingesting endpoint '%s' (limit=%d)", endpoint, limit)

        while processed < limit:
            batch_limit = min(BATCH_SIZE, limit - processed)
            items = client.fetch(endpoint, limit=batch_limit, offset=offset, date_from=date_from, country=country)
            if not items:
                break

            # Phase 1: parse + optionally enrich with PDF content
            doc_batch: List[Tuple[Dict[str, Any], List[Dict[str, Any]]]] = []
            for raw in items:
                stats.total += 1
                processed += 1
                try:
                    doc = parse(raw, endpoint)
                    if not doc or not doc.get("body"):
                        stats.skipped += 1
                        continue

                    # Optionally replace body with PDF text (richer content)
                    if settings.FETCH_PDF_CONTENT and doc.get("pdf_url", "").lower().endswith(".pdf"):
                        from ingestion.file_loader import fetch_pdf_text
                        pdf_text = fetch_pdf_text(doc["pdf_url"])
                        if pdf_text and pdf_text.strip():
                            doc["body"] = pdf_text

                    chunks = chunk_document(doc)
                    if not chunks:
                        stats.skipped += 1
                        continue

                    doc_batch.append((doc, chunks))
                except Exception as e:
                    stats.failed += 1
                    if len(stats.errors) < 10:
                        stats.errors.append({"error": str(e)})
                    logger.warning("Parse/chunk failed for item in %s: %s", endpoint, e)

            if not doc_batch:
                offset += batch_limit
                continue

            # Phase 2: delete orphan chunks from previous ingestions
            for doc, _ in doc_batch:
                store.delete_document_chunks(doc["id"])

            # Phase 3: embed all chunks together (cross-document batching)
            all_chunks = [c for _, chunks in doc_batch for c in chunks]
            try:
                texts = [c["content"] for c in all_chunks]
                all_embeddings = embedder.embed_documents(texts)
                store.upsert_chunks(all_chunks, all_embeddings)
                stats.succeeded += len(doc_batch)
            except Exception as e:
                stats.failed += len(doc_batch)
                logger.error(
                    "Batch embed/upsert failed for %d docs (%d chunks): %s",
                    len(doc_batch), len(all_chunks), e,
                )
                if len(stats.errors) < 10:
                    stats.errors.append({"batch_docs": len(doc_batch), "error": str(e)})

            offset += batch_limit
            elapsed = time.time() - start_time
            rate = stats.succeeded / elapsed if elapsed > 0 else 0
            eta_min = (limit - processed) / rate / 60 if rate > 0 else 0
            logger.info(
                "%s: %d/%d processed (%d OK, %d failed, %d skipped) — %.1f docs/sec, ETA %.0f min",
                endpoint, processed, limit,
                stats.succeeded, stats.failed, stats.skipped,
                rate, eta_min,
            )

        logger.info(
            "Endpoint '%s' complete: %d succeeded, %d failed, %d skipped",
            endpoint, stats.succeeded, stats.failed, stats.skipped,
        )
        all_stats[endpoint] = stats

    logger.info("Ingestion pipeline complete.")
    return all_stats
