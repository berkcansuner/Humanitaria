import logging
import time
from typing import List, Dict, Any, Optional, Set

from pinecone import Pinecone

from config import get_settings

logger = logging.getLogger(__name__)


class PineconeStore:
    """Pinecone serverless write-side store.

    Serverless indexes do NOT support delete-by-metadata-filter, so orphan
    cleanup uses the deterministic chunk-id prefix ({doc_id}_) via list+delete.
    """

    def __init__(self):
        self.settings = get_settings()
        self.pc = Pinecone(api_key=self.settings.PINECONE_API_KEY)
        self.index = self.pc.Index(self.settings.PINECONE_INDEX)
        self.namespace = self.settings.PINECONE_NAMESPACE or None

    def clear_collection(self) -> None:
        """Delete every vector in the namespace (full re-ingest)."""
        try:
            self.index.delete(delete_all=True, namespace=self.namespace)
            logger.info("Cleared Pinecone namespace %s", self.namespace)
        except Exception as e:
            # Namespace may not exist yet on first ingest — non-fatal.
            logger.warning("Failed to clear Pinecone namespace %s: %s", self.namespace, e)

    def delete_document_chunks(self, doc_id: str, keep_ids: Optional[Set[str]] = None) -> None:
        """Delete previously stored chunks for *doc_id* via id-prefix listing.

        If *keep_ids* is given, chunks whose id is in that set are preserved. This
        is used to prune only surplus/stale chunks *after* an overwrite-upsert, so a
        document is never left with zero vectors if a write fails midway.
        """
        try:
            ids: List[str] = []
            for page in self.index.list(prefix=f"{doc_id}_", namespace=self.namespace):
                ids.extend(page)
            if keep_ids is not None:
                ids = [i for i in ids if i not in keep_ids]
            # Pinecone delete accepts at most 1000 ids per request.
            for i in range(0, len(ids), 1000):
                self.index.delete(ids=ids[i : i + 1000], namespace=self.namespace)
        except Exception as e:
            logger.debug("delete_document_chunks no-op for doc_id=%s: %s", doc_id, e)

    # Pinecone caps a single upsert request at ~4 MB. With 3072-dim float
    # vectors + text metadata (~18 KB/vector), batches of 100 stay well under.
    _UPSERT_BATCH = 100
    # Pinecone serverless rate-limits writes (429) under sustained volume.
    # Exponential backoff: 1+2+4+8+16s across 5 retries before giving up.
    _UPSERT_MAX_RETRIES = 6

    def _upsert_batch(self, batch: List[Dict[str, Any]]) -> None:
        """Upsert one batch, retrying with exponential backoff on 429 rate limits."""
        backoff = 1.0
        for attempt in range(self._UPSERT_MAX_RETRIES):
            try:
                self.index.upsert(vectors=batch, namespace=self.namespace)
                return
            except Exception as e:
                rate_limited = getattr(e, "status", None) == 429 or "429" in str(e)
                if rate_limited and attempt < self._UPSERT_MAX_RETRIES - 1:
                    logger.warning("Pinecone upsert rate-limited (429), backing off %.1fs (attempt %d)",
                                   backoff, attempt + 1)
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise

    def upsert_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> None:
        if not chunks:
            return
        vectors = [
            {
                "id": c["id"],
                "values": emb,
                # Store page content under "text" so langchain-pinecone read-side
                # (text_key="text") returns it as Document.page_content.
                "metadata": {**c["metadata"], "text": c["content"]},
            }
            for c, emb in zip(chunks, embeddings)
        ]
        try:
            for i in range(0, len(vectors), self._UPSERT_BATCH):
                self._upsert_batch(vectors[i : i + self._UPSERT_BATCH])
            logger.info("Upserted %d chunks into Pinecone", len(chunks))
        except Exception as e:
            logger.error("Failed to upsert %d chunks into Pinecone: %s", len(chunks), e)
            raise


def get_store():
    return PineconeStore()
