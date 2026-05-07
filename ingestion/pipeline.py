import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from ingestion.client import ReliefWebClient, ENDPOINT_CONFIG
from ingestion.parser import parse
from ingestion.chunker import chunk_document
from ingestion.embedder import OllamaEmbedder
from ingestion.store import ChromaStore

logger = logging.getLogger(__name__)


@dataclass
class IngestionStats:
    endpoint: str
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list = field(default_factory=list)


def run_pipeline(
    limit: int = 100,
    force: bool = False,
    endpoints: Optional[List[str]] = None,
) -> None:
    if endpoints is None:
        endpoints = ["reports"]
    logger.info("Starting ingestion pipeline (limit=%d, force=%s, endpoints=%s)", limit, force, endpoints)
    client = ReliefWebClient()
    embedder = OllamaEmbedder()
    store = ChromaStore()
    if force:
        store.clear_collection()
    for endpoint in endpoints:
        offset = 0
        total_processed = 0
        logger.info("Ingesting endpoint '%s' (limit=%d)", endpoint, limit)
        while total_processed < limit:
            batch_limit = min(100, limit - total_processed)
            items = client.fetch(endpoint, limit=batch_limit, offset=offset)
            if not items:
                break
            for raw in items:
                doc = parse(raw, endpoint)
                if not doc.get("body"):
                    continue
                chunks = chunk_document(doc)
                if not chunks:
                    continue
                texts = [c["content"] for c in chunks]
                embeddings = embedder.embed_batch(texts)
                store.upsert_chunks(chunks, embeddings)
                total_processed += 1
            offset += batch_limit
        logger.info("Endpoint '%s' complete. Processed %d documents.", endpoint, total_processed)
    logger.info("Ingestion pipeline complete.")