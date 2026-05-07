import json
import logging
from uuid import uuid4
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from langchain_core.messages import HumanMessage, AIMessage
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from rag.query_processor import extract_filters
from rag.retriever import build_retriever
from rag.chain import build_chain
from rag.history import get_session_history, populate_history_from_messages

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []
    session_id: Optional[str] = None


class SourceDocument(BaseModel):
    title: str
    url: str
    date: Optional[str] = None
    country: Optional[str] = None
    source: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceDocument]
    session_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid4())

    if not req.session_id and req.history:
        msgs = []
        for m in req.history:
            if m.role == "user":
                msgs.append(HumanMessage(content=m.content))
            elif m.role == "assistant":
                msgs.append(AIMessage(content=m.content))
        populate_history_from_messages(session_id, msgs)

    filters = extract_filters(req.message)
    retriever = build_retriever(filter=filters if filters else None)
    docs = await retriever.ainvoke(req.message)

    context = "\n\n---\n\n".join(doc.page_content for doc in docs)
    sources = [
        SourceDocument(
            title=doc.metadata.get("title", "Belirsiz"),
            url=doc.metadata.get("url", ""),
            date=doc.metadata.get("date"),
            country=doc.metadata.get("country"),
            source=doc.metadata.get("source"),
        )
        for doc in docs
    ]

    chain = build_chain()
    answer = await chain.ainvoke(
        {"question": req.message, "context": context},
        config={"configurable": {"session_id": session_id}},
    )

    return ChatResponse(answer=answer, sources=sources, session_id=session_id)


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    session_id = req.session_id or str(uuid4())

    if not req.session_id and req.history:
        msgs = []
        for m in req.history:
            if m.role == "user":
                msgs.append(HumanMessage(content=m.content))
            elif m.role == "assistant":
                msgs.append(AIMessage(content=m.content))
        populate_history_from_messages(session_id, msgs)

    filters = extract_filters(req.message)
    retriever = build_retriever(filter=filters if filters else None)
    docs = await retriever.ainvoke(req.message)

    sources = [
        {
            "title": doc.metadata.get("title", "Belirsiz"),
            "url": doc.metadata.get("url", ""),
            "date": doc.metadata.get("date"),
            "country": doc.metadata.get("country"),
            "source": doc.metadata.get("source"),
        }
        for doc in docs
    ]
    context = "\n\n---\n\n".join(doc.page_content for doc in docs)
    chain = build_chain()

    async def event_generator():
        try:
            async for chunk in chain.astream(
                {"question": req.message, "context": context},
                config={"configurable": {"session_id": session_id}},
            ):
                if chunk:
                    yield ServerSentEvent(
                        event="token",
                        data=json.dumps({"content": chunk}, ensure_ascii=False),
                    )

            if sources:
                yield ServerSentEvent(
                    event="sources",
                    data=json.dumps({"sources": sources}, ensure_ascii=False),
                )

            yield ServerSentEvent(
                event="session",
                data=json.dumps({"session_id": session_id}),
            )
            yield ServerSentEvent(event="done", data="{}")

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield ServerSentEvent(
                event="error",
                data=json.dumps({"message": str(e)}, ensure_ascii=False),
            )
            yield ServerSentEvent(event="done", data="{}")

    return EventSourceResponse(event_generator())