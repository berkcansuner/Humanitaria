"""Conversation CRUD endpoints backing the sidebar.

Auth uses the same optional API-key dependency as the chat routes. The per-IP
chat rate limiter is intentionally NOT applied here: these endpoints are cheap
(no LLM call) and the sidebar polls them, so the 20/minute chat budget would
throttle normal use. Sync SQLite calls are offloaded with anyio.to_thread.
"""
import logging
from typing import List, Optional

import anyio
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from uuid import uuid4

from api.routes.chat import require_api_key
from rag import conversations as store
from rag.history import clear_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", dependencies=[Depends(require_api_key)])


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    sources: Optional[list] = None
    created_at: str


class CreateConversationIn(BaseModel):
    title: Optional[str] = Field(default="Yeni sohbet", max_length=200)


class RenameIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


@router.get("", response_model=List[ConversationOut])
async def list_conversations():
    return await anyio.to_thread.run_sync(store.list_conversations)


@router.post("", response_model=ConversationOut)
async def create_conversation(body: CreateConversationIn):
    conv_id = str(uuid4())
    await anyio.to_thread.run_sync(store.create_conversation, conv_id, body.title)
    rows = await anyio.to_thread.run_sync(store.list_conversations)
    for r in rows:
        if r["id"] == conv_id:
            return r
    raise HTTPException(status_code=500, detail="Conversation create failed")


@router.get("/{conv_id}/messages", response_model=List[MessageOut])
async def get_messages(conv_id: str):
    if not await anyio.to_thread.run_sync(store.conversation_exists, conv_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return await anyio.to_thread.run_sync(store.get_messages, conv_id)


@router.patch("/{conv_id}", response_model=ConversationOut)
async def rename_conversation(conv_id: str, body: RenameIn):
    if not await anyio.to_thread.run_sync(store.conversation_exists, conv_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    await anyio.to_thread.run_sync(store.rename_conversation, conv_id, body.title)
    rows = await anyio.to_thread.run_sync(store.list_conversations)
    return next(r for r in rows if r["id"] == conv_id)


@router.delete("/{conv_id}", status_code=204)
async def delete_conversation(conv_id: str):
    await anyio.to_thread.run_sync(store.delete_conversation, conv_id)
    # Drop the in-memory window too so a stale session can't linger.
    clear_session(conv_id)
