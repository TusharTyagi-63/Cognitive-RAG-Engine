"""
backend/app/models/user.py
===========================
ORM model for the ``users`` table.

Design Decisions:
-----------------
- ``username`` and ``email`` are both UNIQUE and INDEXED at the database level
  so lookups during authentication and profile resolution are fast.
- ``hashed_password`` is stored with a generous VARCHAR(255) to accommodate
  modern Argon2/bcrypt hashes without risk of truncation.
- ``is_active`` allows soft-disabling accounts without deleting data.
- ``is_superuser`` gates access to admin-only endpoints.
- Both ``documents`` and ``chat_sessions`` relationships use
  ``cascade="all, delete-orphan"`` so removing a User automatically removes
  all their owned resources — preventing orphaned rows and referential-integrity
  violations.
- ``back_populates`` is used on every relationship to keep the ORM graph
  bidirectional and explicit (no implicit ``backref`` magic).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base_model import BaseModel

if TYPE_CHECKING:
    from backend.app.models.chat_session import ChatSession
    from backend.app.models.document import Document


class User(BaseModel):
    """
    Represents a registered user of the Cognitive RAG Engine.

    Columns
    -------
    username        : Unique display name (3-50 characters).
    email           : Unique e-mail address (max 255 characters).
    hashed_password : Bcrypt / Argon2 hash of the user's password.
    is_active       : Whether the account is enabled.
    is_superuser    : Whether the user has admin privileges.
    """

    __tablename__ = "users"

    __table_args__ = (
        CheckConstraint(
            "length(username) >= 3",
            name="ck_users_username_min_length",
        ),
        CheckConstraint(
            "length(email) >= 5",
            name="ck_users_email_min_length",
        ),
    )

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique display name — 3 to 50 characters.",
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique e-mail address used for login and notifications.",
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Password hash (Argon2 / bcrypt).",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
        comment="Soft-disable flag — inactive users cannot authenticate.",
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        comment="Admin privilege flag.",
    )

    # ── Relationships ──────────────────────────────────────────────────
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    chat_sessions: Mapped[List["ChatSession"]] = relationship(
        "ChatSession",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} username={self.username!r}>"
