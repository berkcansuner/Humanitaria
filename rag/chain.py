import logging
from typing import Dict, Any, Optional
from langchain.chains import ConversationalRetrievalChain
from langchain_community.chat_models import ChatOllama
from config import get_settings
from rag.retriever import build_retriever
from rag.memory import build_memory

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "Sen ReliefWeb veritabanındaki insani yardım belgelerini analiz eden asistansın.\n"
    "YALNIZCA sağlanan belgelerden yararlan. Belgede olmayan bilgileri uydurma.\n"
    "Kullanıcının dilinde yanıt ver (Türkçe veya İngilizce).\n"
    "Tarih veya ülke filtresi uygulandıysa bunu yanıtın başında belirt.\n"
    "Her yanıtın sonunda kullandığın kaynak URL ve tarihlerini listele."
)

def build_chain(filter: Optional[Dict[str, Any]] = None):
    settings = get_settings()
    llm = ChatOllama(
        model=settings.OLLAMA_LLM_MODEL,
        base_url=settings.OLLAMA_CLOUD_BASE_URL,
        api_key=settings.OLLAMA_CLOUD_API_KEY,
        temperature=0.3,
    )
    retriever = build_retriever(filter=filter)
    memory = build_memory()
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        return_source_documents=True,
        combine_docs_chain_kwargs={"prompt": _SYSTEM_PROMPT},
    )
    return chain
