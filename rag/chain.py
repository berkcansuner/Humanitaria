import logging

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from config import get_settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are an assistant that analyzes humanitarian aid documents from the ReliefWeb database.\n"
    "Rules:\n"
    "1. Only provide information from the documents in the supplied Context. Never fabricate or guess.\n"
    "2. Answer in the user's language (e.g. English or Turkish) — match the language of the question.\n"
    "3. Respond briefly and politely to general greetings or questions unrelated to the documents, without citing sources.\n"
    "4. For document-based questions, take the information from the documents. Do NOT write source titles or a source "
    "list in the body — sources are shown in a separate SOURCES section below; you only add [n] citations.\n"
    "5. If a date or country filter was applied, state it at the beginning of your answer.\n"
    "6. Do NOT add a 'Sources:' section — the source list is shown separately in the interface.\n"
    "6a. Each document in the Context starts with an [n] number. At the end of a sentence/statement where you use "
    "information from a document, append that document's number as [n] (e.g. 'Clashes intensified [2].'). Cite ONLY "
    "the documents you actually used; do not cite documents you did not use and do not invent numbers.\n"
    "7. If the query is vague (no country, date, or topic specified), briefly note in your answer what information is "
    "missing and which details the user could provide (country, time period, topic).\n"
    "8. If the Context section is empty or contains documents irrelevant to the question, tell the user — in their own "
    "language — that no relevant documents were found in the database and suggest specifying a more specific country, "
    "topic, or date range, or that new documents may need to be added. Never answer from your own general knowledge."
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
    if settings.CHAT_LLM_PROVIDER == "gemini":
        # Gemini via OpenAI-compatible endpoint — same ChatOpenAI interface
        llm = ChatOpenAI(
            model=settings.GEMINI_LLM_MODEL,
            base_url=settings.GEMINI_BASE_URL,
            api_key=settings.GEMINI_API_KEY,
            temperature=0.3,
            streaming=True,
        )
        logger.info("Chat LLM provider: gemini (%s)", settings.GEMINI_LLM_MODEL)
    else:
        llm = ChatOpenAI(
            model=settings.OLLAMA_LLM_MODEL,
            base_url=settings.OLLAMA_CLOUD_BASE_URL,
            api_key=settings.OLLAMA_CLOUD_API_KEY,
            temperature=0.3,
            streaming=True,
        )
        logger.info("Chat LLM provider: ollama (%s)", settings.OLLAMA_LLM_MODEL)

    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM_PROMPT + "\n\nContext:\n{context}"),
        MessagesPlaceholder("chat_history"),
        ("human", "{question}"),
    ])

    _chain = prompt | llm | StrOutputParser()
    return _chain
