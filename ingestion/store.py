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
            metadata={"hnsw:space": "cosine"}
        )

    def clear_collection(self) -> None:
        """Delete and recreate the collection to force full re-ingestion."""
        try:
            self.client.delete_collection(name=self.settings.CHROMA_COLLECTION)
            logger.info("Deleted collection %s", self.settings.CHROMA_COLLECTION)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            name=self.settings.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info("Recreated collection %s", self.settings.CHROMA_COLLECTION)

    def upsert_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> None:
        if not chunks:
            return
        ids = [c["id"] for c in chunks]
        documents = [c["content"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info("Upserted %d chunks into ChromaDB", len(chunks))
