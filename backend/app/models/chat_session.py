"""
backend/app/models/chat_session.py
===================================
ORM model for the ``chat_sessions`` table.

Design Decisions:
-----------------
- Each chat session belongs to exactly one user (``user_id`` FK).
- ``title`` defaults to ``"New Chat"`` at both the Python and database level
  so the UI always has something to display in the sidebar.
- ``messages`` uses ``cascade="all, delete-orphan"`` — deleting a session
  automatically purges its entire message history, preventing orphaned rows.
- The ``order_by`` on the messages relationship is intentionally omitted here;
  ordering is handled at query time via the composite index on
  ``(session_id, timestamp)`` defined in the ``Message`` model.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, List

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base_model import BaseModel

if TYPE_CHECKING:
    from backend.app.models.message import Message
    from backend.app.models.user import User


class ChatSession(BaseModel):
    """
    Represents a single chat conversation between a user and the RAG assistant.

    Columns
    -------
    user_id : Owner's UUID (FK → users.id).
    title   : Human-readable session title (max 200 chars).
    """

    __tablename__ = "chat_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="FK → users.id — owner of this chat session.",
    )
    title: Mapped[str] = mapped_column(
        String(200),
        default="New Chat",
        server_default="New Chat",
        nullable=False,
        comment="Display title for this chat session.",
    )

    # ── Relationships ──────────────────────────────────────────────────
    user: Mapped["User"] = relationship(
        "User",
        back_populates="chat_sessions",
        lazy="joined",
    )
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ChatSession id={self.id} title={self.title!r}>"
