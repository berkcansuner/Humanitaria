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
from rag.retriever import build_retriever, rerank_by_recency
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
        docs = rerank_by_recency(docs)

        context = "\n\n---\n\n".join(doc.page_content for doc in docs)
        sources = [
            SourceDocument(
                title=doc.metadata.get("title", "Belirsiz"),
                url=doc.metadata.get("url", ""),
                date=doc.metadata.get("date"),
                country=doc.metadata.get("country"),
                source=doc.metadata.get("source"),
                doctype=doc.metadata.get("doctype"),
            )
            for doc in docs
            if doc.metadata.get("url") and doc.metadata.get("title")
        ]

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
            docs = rerank_by_recency(docs)

            analysis = analyze_query(req.message, filters=filters)

            sources = [
                {
                    "title": doc.metadata.get("title", "Belirsiz"),
                    "url": doc.metadata.get("url", ""),
                    "date": doc.metadata.get("date"),
                    "country": doc.metadata.get("country"),
                    "source": doc.metadata.get("source"),
                    "doctype": doc.metadata.get("doctype"),
                }
                for doc in docs
                if doc.metadata.get("url") and doc.metadata.get("title")
            ]
            context = "\n\n---\n\n".join(doc.page_content for doc in docs)

            history = get_session_history(session_id)
            chat_history = list(history.messages)

            chain = build_chain()

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

            if sources:
                yield ServerSentEvent(
                    event="sources",
                    data=json.dumps({"sources": sources}, ensure_ascii=False),
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
