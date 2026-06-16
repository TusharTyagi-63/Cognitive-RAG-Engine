"""
backend/app/models/message.py
==============================
ORM model for the ``messages`` table.

Design Decisions:
-----------------
- ``role`` is constrained by a CHECK to exactly three allowed values
  (``user``, ``assistant``, ``system``), matching the OpenAI chat-completion
  message format.  Using a DB-level constraint rather than an application-level
  enum keeps the data clean even when rows are inserted outside the ORM.
- ``content`` uses the ``Text`` type (unlimited length) because assistant
  responses may contain very long Markdown, code blocks, or embedded JSON.
- A **composite index** on ``(session_id, timestamp)`` is added to accelerate
  the most critical query: "fetch all messages in a session, ordered by time."
  This index supports both the filter and the sort in a single B-tree scan.
- ``timestamp`` defaults to the database ``now()`` so the clock source is
  consistent regardless of which application instance writes the row.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base_model import BaseModel

if TYPE_CHECKING:
    from backend.app.models.chat_session import ChatSession


class Message(BaseModel):
    """
    A single message within a ChatSession.

    Columns
    -------
    session_id : FK → chat_sessions.id.
    role       : One of 'user', 'assistant', or 'system'.
    content    : Full message body (Markdown / plain text).
    timestamp  : Server-side UTC timestamp of when the message was created.
    """

    __tablename__ = "messages"

    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant', 'system')",
            name="ck_messages_role_valid",
        ),
        Index(
            "ix_messages_session_id_timestamp",
            "session_id",
            "timestamp",
        ),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="FK → chat_sessions.id — parent session.",
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Message role: 'user', 'assistant', or 'system'.",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full message body.",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="UTC timestamp of message creation.",
    )

    # ── Relationships ──────────────────────────────────────────────────
    session: Mapped["ChatSession"] = relationship(
        "ChatSession",
        back_populates="messages",
        lazy="joined",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Message id={self.id} role={self.role!r}>"
