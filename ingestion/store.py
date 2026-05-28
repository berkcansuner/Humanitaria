import logging
from typing import List, Dict, Any

import chromadb

from config import get_settings

logger = logging.getLogger(__name__)


class ChromaStore:
    def __init__(self):
        self.settings = get_settings()
        self.client = chromadb.PersistentClient(path=self.settings.CHROMA_DB_PATH)
        self.collection = self.client.get_or_create_collection(
            name=self.settings.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

    def clear_collection(self) -> None:
        """Delete and recreate the collection to force full re-ingestion."""
        try:
            self.client.delete_collection(name=self.settings.CHROMA_COLLECTION)
            logger.info("Deleted collection %s", self.settings.CHROMA_COLLECTION)
        except Exception as e:
            logger.warning("Failed to clear collection %s: %s", self.settings.CHROMA_COLLECTION, e)
        self.collection = self.client.get_or_create_collection(
            name=self.settings.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("Recreated collection %s", self.settings.CHROMA_COLLECTION)

    def delete_document_chunks(self, doc_id: str) -> None:
        """Delete all previously stored chunks for *doc_id*.

        Called before upserting new chunks so that orphan chunks from a
        shrunken document are not left in the collection.
        """
        try:
            self.collection.delete(where={"doc_id": {"$eq": doc_id}})
        except Exception as e:
            # No matching chunks is normal on first ingest — log at debug only.
            logger.debug("delete_document_chunks no-op for doc_id=%s: %s", doc_id, e)

    def upsert_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> None:
        if not chunks:
            return
        ids = [c["id"] for c in chunks]
        documents = [c["content"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        try:
            self.collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
            logger.info("Upserted %d chunks into ChromaDB", len(chunks))
        except Exception as e:
            logger.error("Failed to upsert %d chunks into ChromaDB: %s", len(chunks), e)
            raise
