import logging
from typing import Dict, Any, Optional
import chromadb
from langchain_core.documents import Document
from config import get_settings

logger = logging.getLogger(__name__)

def build_retriever(filter: Optional[Dict[str, Any]] = None):
    settings = get_settings()
    client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
    collection = client.get_collection(name=settings.CHROMA_COLLECTION)
    def _retrieve(query: str, k: int = None) -> list:
        top_k = k or settings.TOP_K_RETRIEVAL
        results = collection.query(
            query_texts=[query],
            n_results=top_k,
            where=filter if filter else None,
        )
        docs = []
        for i, doc_text in enumerate(results.get("documents", [[]])[0]):
            metadata = results.get("metadatas", [[]])[0][i] if results.get("metadatas") else {}
            docs.append(Document(page_content=doc_text, metadata=metadata or {}))
        return docs
    return _retrieve
