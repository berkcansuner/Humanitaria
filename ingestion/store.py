import logging
from typing import List, Dict, Any

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

    def delete_document_chunks(self, doc_id: str) -> None:
        """Delete all previously stored chunks for *doc_id* via id-prefix listing."""
        try:
            ids: List[str] = []
            for page in self.index.list(prefix=f"{doc_id}_", namespace=self.namespace):
                ids.extend(page)
            # Pinecone delete accepts at most 1000 ids per request.
            for i in range(0, len(ids), 1000):
                self.index.delete(ids=ids[i : i + 1000], namespace=self.namespace)
        except Exception as e:
            logger.debug("delete_document_chunks no-op for doc_id=%s: %s", doc_id, e)

    # Pinecone caps a single upsert request at ~4 MB. With 3072-dim float
    # vectors + text metadata (~18 KB/vector), batches of 100 stay well under.
    _UPSERT_BATCH = 100

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
                self.index.upsert(
                    vectors=vectors[i : i + self._UPSERT_BATCH], namespace=self.namespace
                )
            logger.info("Upserted %d chunks into Pinecone", len(chunks))
        except Exception as e:
            logger.error("Failed to upsert %d chunks into Pinecone: %s", len(chunks), e)
            raise


def get_store():
    return PineconeStore()
