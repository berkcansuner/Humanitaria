import logging
from typing import Dict, Any, Optional
from langchain_community.vectorstores import Chroma
from config import get_settings
from rag.embeddings import OllamaLangChainEmbeddings

logger = logging.getLogger(__name__)

def build_retriever(filter: Optional[Dict[str, Any]] = None):
    settings = get_settings()
    embeddings = OllamaLangChainEmbeddings()
    vectorstore = Chroma(
        collection_name=settings.CHROMA_COLLECTION,
        persist_directory=settings.CHROMA_DB_PATH,
        embedding_function=embeddings,
    )
    return vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": settings.TOP_K_RETRIEVAL, "filter": filter if filter else None}
    )
