import logging
from typing import List, Dict, Any
from ingestion.client import ReliefWebClient
from ingestion.parser import parse_report
from ingestion.chunker import chunk_document
from ingestion.embedder import OllamaEmbedder
from ingestion.store import ChromaStore

logger = logging.getLogger(__name__)

def run_pipeline(limit: int = 100, force: bool = False) -> None:
    logger.info("Starting ingestion pipeline (limit=%d, force=%s)", limit, force)
    client = ReliefWebClient()
    embedder = OllamaEmbedder()
    store = ChromaStore()
    offset = 0
    total_processed = 0
    while total_processed < limit:
        batch_limit = min(100, limit - total_processed)
        reports = client.fetch_reports(limit=batch_limit, offset=offset)
        if not reports:
            break
        for raw in reports:
            doc = parse_report(raw)
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
    logger.info("Ingestion pipeline complete. Processed %d reports.", total_processed)
