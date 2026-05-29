import logging

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from config import get_settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "Sen ReliefWeb veritabanındaki insani yardım belgelerini analiz eden asistansın.\n"
    "Kurallar:\n"
    "1. Sadece sağlanan belgelerden bilgi ver. Bilgi uydurma.\n"
    "2. Kullanıcının dilinde yanıt ver (Türkçe veya İngilizce).\n"
    "3. Genel selamlaşma veya belgelerle ilgili olmayan sorulara kısa ve nazikçe yanıt ver, kaynak gösterme.\n"
    "4. Belge tabanlı sorularda, bilgiyi belgeden al ve kaynak belge başlığını doğal olarak belirt.\n"
    "5. Tarih veya ülke filtresi uygulandıysa yanıtın başında belirt.\n"
    "6. 'Kaynaklar:' bölümü ekleme — kaynakları yanıt metni içinde doğal olarak ver.\n"
    "7. Eğer sorgu belirsizse (ülke, tarih veya konu belirtilmemişse), yanıtında hangi bilgilerin eksik olduğunu ve "
    "kullanıcının hangi detayları belirtebileceğini (ülke, zaman aralığı, konu) kısaça belirt."
)

_chain: Runnable | None = None


def build_chain() -> Runnable:
    """Return the cached LCEL chain (prompt | llm | StrOutputParser).

    History management is intentionally external: callers retrieve
    the session history, pass it as chat_history, and persist the
    new exchange after the chain returns.  This replaces the now-
    deprecated RunnableWithMessageHistory wrapper.

    Input keys expected by the chain:
      - question:     str   — the user's message
      - context:      str   — retrieved document text
      - chat_history: list  — list of BaseMessage from rag.history
    """
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

    _chain = prompt | llm | StrOutputParser()
    return _chain
