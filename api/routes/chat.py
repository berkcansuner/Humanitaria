from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

from rag.query_processor import extract_filters
from rag.chain import build_chain
from rag.memory import build_memory
from langchain.schema import HumanMessage, AIMessage

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []


class SourceDocument(BaseModel):
    title: str
    url: str
    date: Optional[str] = None
    country: Optional[str] = None
    source: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceDocument]


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    filters = extract_filters(req.message)
    memory = build_memory()
    for msg in (req.history or []):
        if msg.role == "user":
            memory.chat_memory.add_message(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            memory.chat_memory.add_message(AIMessage(content=msg.content))
    chain = build_chain(filter=filters if filters else None, memory=memory)
    result = chain.invoke({"question": req.message})
    answer = result.get("answer", "")
    source_docs = result.get("source_documents", [])
    sources = []
    for doc in source_docs:
        meta = doc.metadata
        sources.append(SourceDocument(
            title=meta.get("title", "Belirsiz"),
            url=meta.get("url", ""),
            date=meta.get("date"),
            country=meta.get("country"),
            source=meta.get("source"),
        ))
    return ChatResponse(answer=answer, sources=sources)
