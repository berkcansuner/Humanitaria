import json
import logging
import re
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import List, Literal, Optional
from langchain_core.messages import HumanMessage, AIMessage
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from rag.query_processor import extract_filters, analyze_query
from rag.retriever import build_retriever, rerank_by_recency, apply_date_filter
from rag.chain import build_chain
from rag.history import get_session_history

logger = logging.getLogger(__name__)

router = APIRouter()

_GREETING_PATTERN = re.compile(
    r'^(merhaba|selam|hey|hi|hello|good\s*(morning|afternoon|evening)|nasılsın|how are you|günaydın|iyi\s*günler)[\s!.?]*$',
    re.IGNORECASE | re.UNICODE,
)

_GREETING_REPLY = "Merhaba! Size insani yardım raporları hakkında nasıl yardımcı olabilirim?"


def _is_greeting(text: str) -> bool:
    return bool(_GREETING_PATTERN.match(text.strip()))


def _no_docs_message(filters: dict) -> str:
    """Return a clear Turkish/English message when the retriever finds nothing."""
    parts = []
    if filters.get("country"):
        parts.append(f"**{filters['country']}**")
    if filters.get("theme"):
        parts.append(f"**{filters['theme']}**")
    if filters.get("date"):
        parts.append("belirtilen tarih aralığı")
    scope = " + ".join(parts) if parts else "bu sorgu"
    return (
        f"Veritabanımızda {scope} için eşleşen belge bulunamadı.\n\n"
        "Farklı bir ülke, konu ya da tarih aralığı deneyebilir veya sorunuzu "
        "daha genel bir şekilde ifade edebilirsiniz."
    )


_CITATION_PATTERN = re.compile(r"\[(\d+)\]")


def _build_context_and_sources(docs):
    """Number retrieved docs [1..N] for the prompt and build matching source dicts.

    The index is the doc's 1-based position so an inline [n] marker in the answer
    maps back to the same source. Docs without a url/title still consume an index
    (keeping numbering aligned) but are not surfaced as sources.
    """
    context = "\n\n---\n\n".join(
        f"[{i}] {doc.page_content}" for i, doc in enumerate(docs, 1)
    )
    sources = [
        {
            "index": i,
            "title": doc.metadata.get("title", "Belirsiz"),
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
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid4())

    if _is_greeting(req.message):
        return ChatResponse(answer=_GREETING_REPLY, sources=[], session_id=session_id)

    try:
        filters = extract_filters(req.message)
        retriever = build_retriever(filter=filters if filters else None)
        docs = await retriever.ainvoke(req.message)
        docs = apply_date_filter(docs, filters.get("date"))
        docs = rerank_by_recency(docs)

        if not docs:
            msg = _no_docs_message(filters)
            return ChatResponse(answer=msg, sources=[], session_id=session_id)

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

        sources = [SourceDocument(**d) for d in _filter_cited_sources(answer, source_dicts)]
        return ChatResponse(answer=answer, sources=sources, session_id=session_id)

    except Exception as e:
        logger.error("Chat error: %s", e)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    session_id = req.session_id or str(uuid4())

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
        try:
            filters = extract_filters(req.message)
            retriever = build_retriever(filter=filters if filters else None)
            docs = await retriever.ainvoke(req.message)
            docs = apply_date_filter(docs, filters.get("date"))
            docs = rerank_by_recency(docs)

            if not docs:
                msg = _no_docs_message(filters)
                yield ServerSentEvent(
                    event="token",
                    data=json.dumps({"content": msg}, ensure_ascii=False),
                )
                yield ServerSentEvent(event="session", data=json.dumps({"session_id": session_id}))
                yield ServerSentEvent(event="done", data="{}")
                return

            analysis = analyze_query(req.message, filters=filters)
            context, source_dicts = _build_context_and_sources(docs)

            history = get_session_history(session_id)
            chat_history = list(history.messages)

            chain = build_chain()

            full_response = ""
            async for chunk in chain.astream({
                "question": req.message,
                "context": context,
                "chat_history": chat_history,
            }):
                if chunk:
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

            yield ServerSentEvent(event="session", data=json.dumps({"session_id": session_id}))
            yield ServerSentEvent(event="done", data="{}")

        except Exception as e:
            logger.error("Streaming error: %s", e)
            yield ServerSentEvent(
                event="error",
                data=json.dumps({"message": str(e)}, ensure_ascii=False),
            )
            yield ServerSentEvent(event="done", data="{}")

    return EventSourceResponse(event_generator())
