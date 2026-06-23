import asyncio
import json
import logging
import re
import time
from uuid import uuid4

import anyio
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field, field_validator
from typing import List, Literal, Optional
from langchain_core.messages import HumanMessage, AIMessage
from sse_starlette.sse import EventSourceResponse, ServerSentEvent
from slowapi import Limiter
from slowapi.util import get_remote_address

from config import get_settings
from rag.query_processor import extract_filters, analyze_query, should_boost_recency
from rag.retriever import (
    build_retriever, rerank_by_recency, apply_date_filter,
    dedupe_by_document, rerank_by_relevance,
)
from rag.chain import build_chain
from rag.history import get_session_history, has_session, populate_history_from_messages
from rag.query_rewriter import rewrite_query
from rag import conversations as convo_store
from api.routes.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Per-client-IP rate limiter; the limit string is read from settings at call time.
limiter = Limiter(key_func=get_remote_address)


def _rate_limit() -> str:
    return get_settings().RATE_LIMIT


_GREETING_PATTERN = re.compile(
    r'^(merhaba|selam|hey|hi|hello|good\s*(morning|afternoon|evening)|nasılsın|how are you|günaydın|iyi\s*günler)[\s!.?]*$',
    re.IGNORECASE | re.UNICODE,
)

_GREETING_REPLY = "Hello! How can I help you with humanitarian reports?"


def _is_greeting(text: str) -> bool:
    return bool(_GREETING_PATTERN.match(text.strip()))


def _no_docs_message(filters: dict) -> str:
    """Return a clear message when the retriever finds nothing."""
    parts = []
    if filters.get("country"):
        parts.append(f"**{filters['country']}**")
    if filters.get("theme"):
        parts.append(f"**{filters['theme']}**")
    if filters.get("date"):
        parts.append("the specified date range")
    scope = " + ".join(parts) if parts else "this query"
    return (
        f"No matching documents were found in our database for {scope}.\n\n"
        "You can try a different country, topic, or date range, or rephrase your "
        "question more generally."
    )


_CITATION_PATTERN = re.compile(r"\[(\d+)\]")


def _build_context_and_sources(docs):
    """Number retrieved docs [1..N] for the prompt and build matching source dicts.

    The index is the doc's 1-based position so an inline [n] marker in the answer
    maps back to the same source. Docs without a url/title still consume an index
    (keeping numbering aligned) but are not surfaced as sources.
    """
    context = "\n\n---\n\n".join(
        f"[{i}] ({doc.metadata.get('date') or 'tarih yok'}) {doc.page_content}"
        for i, doc in enumerate(docs, 1)
    )
    sources = [
        {
            "index": i,
            "title": doc.metadata.get("title", "Untitled"),
            "url": doc.metadata.get("url", ""),
            "date": doc.metadata.get("date"),
            "country": doc.metadata.get("country"),
            "source": doc.metadata.get("source"),
            "doctype": doc.metadata.get("doctype"),
        }
        for i, doc in enumerate(docs, 1)
        if doc.metadata.get("url") and doc.metadata.get("title")
    ]
    return context, sources


def _filter_cited_sources(answer_text: str, sources: list) -> list:
    """Keep only sources whose [n] marker appears in the answer.

    Falls back to all sources when the model emitted no (or no matching)
    citation markers, so the user never sees an empty source list.
    """
    cited = {int(n) for n in _CITATION_PATTERN.findall(answer_text)}
    if not cited:
        return sources
    filtered = [s for s in sources if s.get("index") in cited]
    return filtered or sources


def _derive_title(text: str) -> str:
    """Conversation title = the first user message, whitespace-collapsed and
    truncated. Cheap and avoids an extra LLM call on every new chat."""
    title = re.sub(r"\s+", " ", text).strip()
    return title[:60] if len(title) <= 60 else title[:57] + "..."


def _ensure_conversation_and_seed(user_id: str, session_id: str, message: str) -> None:
    """Create the conversation (owned by user_id) on its first real message, and
    on a cold request for an existing conversation (e.g. after a restart) seed the
    in-memory window from the persistent store so the LLM keeps its context. The
    route has already verified session_id is new or owned by user_id. Sync — call
    via anyio.to_thread.run_sync."""
    if not convo_store.conversation_exists(session_id):
        convo_store.create_conversation(user_id, session_id, _derive_title(message))
    elif not has_session(session_id):
        populate_history_from_messages(
            session_id, convo_store.messages_as_langchain(session_id)
        )


def _verify_session_owner(user_id: str, session_id: str) -> bool:
    """A client-supplied session_id must be brand-new or owned by the user.
    Returns False when it exists but belongs to someone else (cross-user access)."""
    if not convo_store.conversation_exists(session_id):
        return True
    return convo_store.is_owner(user_id, session_id)


def _resolve_retrieval_query(session_id: str, message: str) -> str:
    """Rewrite a follow-up into a standalone retrieval query using in-memory chat
    history. Returns the original message for first turns or when disabled; the
    answer is always generated from the original message."""
    if not get_settings().QUERY_REWRITE_ENABLED or not has_session(session_id):
        return message
    prior = list(get_session_history(session_id).messages)
    return rewrite_query(message, prior) if prior else message


async def _astream_with_retry(chain, payload, retries: int, backoff: float = 1.5):
    """Stream the chat answer, retrying ONLY before the first token.

    Transient upstream errors (Gemini 503 'high demand') reject the request before
    any token is produced, so a short bounded retry can ride them out. Once a token
    has been emitted, a mid-stream error propagates (never duplicate output). The
    LLM client's own retries are disabled (max_retries=0) so this is the single,
    fast-failing retry path."""
    attempt = 0
    while True:
        emitted = False
        try:
            async for chunk in chain.astream(payload):
                emitted = True
                yield chunk
            return
        except Exception:
            if emitted or attempt >= retries:
                raise
            attempt += 1
            await asyncio.sleep(backoff * attempt)


def _persist_exchange(session_id: str, user_message: str, answer: str, sources: list) -> tuple:
    """Persist a completed user+assistant exchange and return the new (user_id,
    assistant_id). Sync — offload to a thread. Only called after the chain
    finishes, so aborted turns are never written."""
    user_id = convo_store.append_message(session_id, "user", user_message)
    assistant_id = convo_store.append_message(session_id, "assistant", answer, sources=sources or None)
    return user_id, assistant_id


async def _retrieve_docs(query: str, filters: dict):
    """Shared retrieval pipeline used by both chat routes.

    candidates (larger k) -> date filter -> dedupe by document ->
    relevance rerank (Pinecone) -> recency blend -> final top-k.

    For "current"-style queries (no explicit date window, no historical intent)
    the recency boost reranks a wider relevance pool by recency so the newest
    reports surface into the final top-k; date-scoped / historical queries keep
    the relevance-first ordering.
    """
    settings = get_settings()
    candidate_k = settings.TOP_K_RETRIEVAL * settings.RERANK_CANDIDATE_MULTIPLIER
    retriever = build_retriever(filter=filters if filters else None, k=candidate_k)
    docs = await retriever.ainvoke(query)
    docs = apply_date_filter(docs, filters.get("date"))
    docs = dedupe_by_document(docs)
    if should_boost_recency(query, filters):
        pool = max(settings.RECENCY_RERANK_POOL, settings.TOP_K_RETRIEVAL)
        docs = rerank_by_relevance(query, docs, pool)
        docs = rerank_by_recency(docs, decay_factor=settings.RECENCY_BOOST_FACTOR)
        docs = docs[:settings.TOP_K_RETRIEVAL]
    else:
        docs = rerank_by_relevance(query, docs, settings.TOP_K_RETRIEVAL)
        docs = rerank_by_recency(docs)
    return docs


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    # history is accepted for backward compatibility but ignored —
    # server-side session history is the single source of truth.
    history: Optional[List[ChatMessage]] = Field(default_factory=list)
    session_id: Optional[str] = None

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message must not be blank")
        return v.strip()


class SourceDocument(BaseModel):
    index: Optional[int] = None
    title: str
    url: str
    date: Optional[str] = None
    country: Optional[str] = None
    source: Optional[str] = None
    doctype: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceDocument]
    session_id: str


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(_rate_limit)
async def chat(request: Request, req: ChatRequest, user: dict = Depends(get_current_user)):
    session_id = req.session_id or str(uuid4())
    if req.session_id and not await anyio.to_thread.run_sync(
        _verify_session_owner, user["id"], session_id
    ):
        raise HTTPException(status_code=404, detail="Conversation not found")

    if _is_greeting(req.message):
        return ChatResponse(answer=_GREETING_REPLY, sources=[], session_id=session_id)

    try:
        retrieval_query = _resolve_retrieval_query(session_id, req.message)
        filters = extract_filters(retrieval_query)
        docs = await _retrieve_docs(retrieval_query, filters)

        if not docs:
            msg = _no_docs_message(filters)
            return ChatResponse(answer=msg, sources=[], session_id=session_id)

        await anyio.to_thread.run_sync(_ensure_conversation_and_seed, user["id"], session_id, req.message)

        context, source_dicts = _build_context_and_sources(docs)

        history = get_session_history(session_id)
        chat_history = list(history.messages)

        chain = build_chain()
        answer = await chain.ainvoke({
            "question": req.message,
            "context": context,
            "chat_history": chat_history,
        })

        history.add_message(HumanMessage(content=req.message))
        history.add_message(AIMessage(content=answer))

        filtered = _filter_cited_sources(answer, source_dicts)
        await anyio.to_thread.run_sync(_persist_exchange, session_id, req.message, answer, filtered)

        sources = [SourceDocument(**d) for d in filtered]
        return ChatResponse(answer=answer, sources=sources, session_id=session_id)

    except Exception as e:
        logger.error("Chat error: %s", e)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")


@router.post("/chat/stream")
@limiter.limit(_rate_limit)
async def chat_stream(request: Request, req: ChatRequest, user: dict = Depends(get_current_user)):
    session_id = req.session_id or str(uuid4())
    if req.session_id and not await anyio.to_thread.run_sync(
        _verify_session_owner, user["id"], session_id
    ):
        raise HTTPException(status_code=404, detail="Conversation not found")

    if _is_greeting(req.message):
        async def greeting_generator():
            yield ServerSentEvent(
                event="token",
                data=json.dumps({"content": _GREETING_REPLY}, ensure_ascii=False),
            )
            yield ServerSentEvent(event="session", data=json.dumps({"session_id": session_id}))
            yield ServerSentEvent(event="done", data="{}")
        return EventSourceResponse(greeting_generator())

    async def event_generator():
        _t0 = time.perf_counter()
        _filter_ms = _retrieval_ms = 0.0
        _ttft_ms = None
        try:
            retrieval_query = _resolve_retrieval_query(session_id, req.message)
            filters = extract_filters(retrieval_query)
            _filter_ms = (time.perf_counter() - _t0) * 1000
            docs = await _retrieve_docs(retrieval_query, filters)
            _retrieval_ms = (time.perf_counter() - _t0) * 1000 - _filter_ms

            if not docs:
                msg = _no_docs_message(filters)
                yield ServerSentEvent(
                    event="token",
                    data=json.dumps({"content": msg}, ensure_ascii=False),
                )
                yield ServerSentEvent(event="session", data=json.dumps({"session_id": session_id}))
                yield ServerSentEvent(event="done", data="{}")
                return

            await anyio.to_thread.run_sync(_ensure_conversation_and_seed, user["id"], session_id, req.message)

            analysis = analyze_query(req.message, filters=filters)
            context, source_dicts = _build_context_and_sources(docs)

            history = get_session_history(session_id)
            chat_history = list(history.messages)

            chain = build_chain()

            full_response = ""
            async for chunk in _astream_with_retry(chain, {
                "question": req.message,
                "context": context,
                "chat_history": chat_history,
            }, get_settings().CHAT_LLM_MAX_RETRIES):
                if chunk:
                    if _ttft_ms is None:
                        _ttft_ms = (time.perf_counter() - _t0) * 1000
                    full_response += chunk
                    yield ServerSentEvent(
                        event="token",
                        data=json.dumps({"content": chunk}, ensure_ascii=False),
                    )

            # Persist the completed exchange to session history
            history.add_message(HumanMessage(content=req.message))
            history.add_message(AIMessage(content=full_response))

            # Surface only the sources the answer actually cited ([n] markers).
            sources = _filter_cited_sources(full_response, source_dicts)

            # Persist to the durable store (runs only after a full stream, so
            # an aborted turn is never written).
            user_msg_id, assistant_msg_id = await anyio.to_thread.run_sync(
                _persist_exchange, session_id, req.message, full_response, sources
            )
            # Tell the client the persisted message ids so it can target a
            # precise cut point for Edit/resend and Regenerate (truncate).
            yield ServerSentEvent(
                event="persisted",
                data=json.dumps({"user_id": user_msg_id, "assistant_id": assistant_msg_id}),
            )

            if sources:
                yield ServerSentEvent(
                    event="sources",
                    data=json.dumps({"sources": sources}, ensure_ascii=False),
                )

            # Follow-up suggestion chips come AFTER the answer (Claude-web-app style).
            if analysis and analysis.get("is_vague"):
                yield ServerSentEvent(
                    event="clarification",
                    data=json.dumps({
                        "message": analysis["message"],
                        "filters": {
                            "country": analysis["has_country"],
                            "date": analysis["has_date"],
                            "theme": analysis["has_theme"],
                        },
                        "suggestions": analysis["suggestions"],
                    }, ensure_ascii=False),
                )

            logger.info(
                "chat latency: filter=%.0fms retrieval=%.0fms ttft=%.0fms total=%.0fms ns=%s",
                _filter_ms, _retrieval_ms, (_ttft_ms if _ttft_ms is not None else -1),
                (time.perf_counter() - _t0) * 1000,
                get_settings().PINECONE_NAMESPACE or "(default)",
            )
            yield ServerSentEvent(event="session", data=json.dumps({"session_id": session_id}))
            yield ServerSentEvent(event="done", data="{}")

        except Exception as e:
            logger.error("Streaming error: %s", e)
            emsg = str(e)
            busy = "503" in emsg or "UNAVAILABLE" in emsg or "high demand" in emsg.lower()
            friendly = (
                "The model is busy right now (high demand). Please try again in a moment."
                if busy else
                "Something went wrong while generating the answer. Please try again."
            )
            yield ServerSentEvent(
                event="error",
                data=json.dumps({"message": friendly}, ensure_ascii=False),
            )
            yield ServerSentEvent(event="done", data="{}")

    return EventSourceResponse(event_generator())
