"""Conversation CRUD endpoints backing the sidebar.

Every endpoint is scoped to the authenticated user (get_current_user): a user
only ever sees or mutates conversations they own; a non-owner gets 404. The
per-IP chat rate limiter is intentionally NOT applied here: these endpoints are
cheap (no LLM call) and the sidebar polls them, so the 20/minute chat budget
would throttle normal use. Sync SQLite calls are offloaded with anyio.to_thread.
"""
import logging
from typing import List, Optional

import anyio
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from uuid import uuid4

from api.routes.auth import get_current_user
from rag import conversations as store
from rag.history import clear_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations")


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
    title: Optional[str] = Field(default="New chat", max_length=200)


class RenameIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


class TruncateIn(BaseModel):
    # Keep messages with id <= this; delete everything after. 0 clears all
    # messages (used when editing the very first message).
    keep_through_message_id: int = Field(..., ge=0)


async def _require_owner(user_id: str, conv_id: str) -> None:
    """404 unless conv_id exists and belongs to user_id (don't leak existence)."""
    if not await anyio.to_thread.run_sync(store.is_owner, user_id, conv_id):
        raise HTTPException(status_code=404, detail="Conversation not found")


@router.get("", response_model=List[ConversationOut])
async def list_conversations(user: dict = Depends(get_current_user)):
    return await anyio.to_thread.run_sync(store.list_conversations, user["id"])


@router.post("", response_model=ConversationOut)
async def create_conversation(body: CreateConversationIn, user: dict = Depends(get_current_user)):
    conv_id = str(uuid4())
    await anyio.to_thread.run_sync(store.create_conversation, user["id"], conv_id, body.title)
    rows = await anyio.to_thread.run_sync(store.list_conversations, user["id"])
    for r in rows:
        if r["id"] == conv_id:
            return r
    raise HTTPException(status_code=500, detail="Conversation create failed")


@router.get("/{conv_id}/messages", response_model=List[MessageOut])
async def get_messages(conv_id: str, user: dict = Depends(get_current_user)):
    await _require_owner(user["id"], conv_id)
    return await anyio.to_thread.run_sync(store.get_messages, conv_id)


@router.patch("/{conv_id}", response_model=ConversationOut)
async def rename_conversation(conv_id: str, body: RenameIn, user: dict = Depends(get_current_user)):
    await _require_owner(user["id"], conv_id)
    await anyio.to_thread.run_sync(store.rename_conversation, conv_id, body.title)
    rows = await anyio.to_thread.run_sync(store.list_conversations, user["id"])
    return next(r for r in rows if r["id"] == conv_id)


@router.delete("/{conv_id}", status_code=204)
async def delete_conversation(conv_id: str, user: dict = Depends(get_current_user)):
    await _require_owner(user["id"], conv_id)
    await anyio.to_thread.run_sync(store.delete_conversation, conv_id)
    # Drop the in-memory window too so a stale session can't linger.
    clear_session(conv_id)


@router.post("/{conv_id}/truncate", status_code=204)
async def truncate_conversation(conv_id: str, body: TruncateIn, user: dict = Depends(get_current_user)):
    """Drop every message after `keep_through_message_id` and rebuild the
    in-memory window. Backs both Edit/resend and Regenerate."""
    await _require_owner(user["id"], conv_id)
    await anyio.to_thread.run_sync(store.truncate_after, conv_id, body.keep_through_message_id)
    await anyio.to_thread.run_sync(store.resync_window, conv_id)
