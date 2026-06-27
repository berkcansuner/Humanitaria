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
    "the documents you actually used. Use ONLY numbers that actually appear as [n] in the Context above; never write a "
    "citation number that is not shown in the Context.\n"
    "7. If the query is vague (no country, date, or topic specified), briefly note in your answer what information is "
    "missing and which details the user could provide (country, time period, topic).\n"
    "8. If the Context section is empty or contains documents irrelevant to the question, tell the user — in their own "
    "language — that no relevant documents were found in the database and suggest specifying a more specific country, "
    "topic, or date range, or that new documents may need to be added. Never answer from your own general knowledge.\n"
    "9. Each document in the Context is labeled with its publication date as (YYYY-MM-DD). For questions about the "
    "current or latest situation, prioritize the most recent documents and state the date range of the information you "
    "used. If the most recent relevant document is old, note that more recent information may not be available."
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
    llm_kwargs = dict(
        model=settings.GEMINI_LLM_MODEL,
        base_url=settings.GEMINI_BASE_URL,
        api_key=settings.GEMINI_API_KEY,
        temperature=0.3,
        streaming=True,
        timeout=settings.CHAT_LLM_TIMEOUT,
        max_retries=0,   # retries handled in the chat route → fast-fail on 503
    )
    # Lower the thinking budget to cut time-to-first-token (kill-switch: "" skips it).
    if settings.GEMINI_REASONING_EFFORT:
        llm_kwargs["reasoning_effort"] = settings.GEMINI_REASONING_EFFORT
    llm = ChatOpenAI(**llm_kwargs)
    logger.info("Chat LLM: gemini (%s) reasoning_effort=%s",
                settings.GEMINI_LLM_MODEL, settings.GEMINI_REASONING_EFFORT or "(default)")

    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM_PROMPT + "\n\nContext:\n{context}"),
        MessagesPlaceholder("chat_history"),
        ("human", "{question}"),
    ])

    _chain = prompt | llm | StrOutputParser()
    return _chain
