"""
backend/app/schemas/chat.py
=============================
Pydantic schemas for ChatSession and Message payloads.

Design Decisions:
-----------------
- **ChatSessionCreate** only requires an optional ``title`` — the ``user_id``
  is injected by the API layer from the authenticated token, not sent by the
  client (preventing impersonation).
- **MessageCreate** constrains ``role`` to a ``Literal["user", "assistant",
  "system"]`` so invalid roles are rejected at the validation boundary rather
  than at the database CHECK constraint.
- **ChatHistoryResponse** bundles session metadata with its ordered list of
  messages, avoiding N+1 queries on the frontend.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import Field

from backend.app.schemas.base import AppBaseModel


class ChatSessionCreate(AppBaseModel):
    """Schema for creating a new chat session."""

    title: Optional[str] = Field(
        "New Chat",
        max_length=200,
        description="Human-readable title for the chat session.",
        examples=["RAG Pipeline Debug"],
    )


class ChatSessionResponse(AppBaseModel):
    """Public chat-session representation."""

    id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class MessageCreate(AppBaseModel):
    """Schema for appending a message to a chat session."""

    content: str = Field(
        ...,
        min_length=1,
        description="Message body (non-empty).",
        examples=["What are the key findings in the uploaded document?"],
    )
    document_ids: Optional[List[UUID]] = Field(
        None,
        description="Optional list of specific document IDs to constrain the RAG search."
    )


class MessageResponse(AppBaseModel):
    """Public message representation."""

    id: UUID
    session_id: UUID
    role: str
    content: str
    timestamp: datetime


class ChatHistoryResponse(AppBaseModel):
    """
    Complete chat history for a session: metadata + ordered messages.

    Returned by the ``GET /sessions/{id}/history`` endpoint.
    """

    session: ChatSessionResponse = Field(
        ...,
        description="Session metadata.",
    )
    messages: List[MessageResponse] = Field(
        ...,
        description="Chronologically ordered list of messages.",
    )
