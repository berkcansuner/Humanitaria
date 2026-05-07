import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
from config import get_settings
from rag.history import get_session_history

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "Sen ReliefWeb veritabanındaki insani yardım belgelerini analiz eden asistansın.\n"
    "YALNIZCA sağlanan belgelerden yararlan. Belgede olmayan bilgileri uydurma.\n"
    "Kullanıcının dilinde yanıt ver (Türkçe veya İngilizce).\n"
    "Tarih veya ülke filtresi uygulandıysa bunu yanıtın başında belirt.\n"
    "Her yanıtın sonunda kullandığın kaynak URL ve tarihlerini listele."
)

_chain: RunnableWithMessageHistory | None = None


def build_chain() -> RunnableWithMessageHistory:
    global _chain
    if _chain is not None:
        return _chain

    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.OLLAMA_LLM_MODEL,
        base_url=settings.OLLAMA_CLOUD_BASE_URL,
        temperature=0.3,
        api_key=settings.OLLAMA_CLOUD_API_KEY,
        streaming=True,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM_PROMPT + "\n\nContext:\n{context}"),
        MessagesPlaceholder("chat_history"),
        ("human", "{question}"),
    ])

    chain = prompt | llm | StrOutputParser()

    _chain = RunnableWithMessageHistory(
        chain,
        get_session_history,
        input_messages_key="question",
        history_messages_key="chat_history",
    )
    return _chain