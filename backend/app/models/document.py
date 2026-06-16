"""
backend/app/models/document.py
===============================
ORM model for the ``documents`` table.

Design Decisions:
-----------------
- ``user_id`` is a non-nullable FK to ``users.id`` with ``ondelete="CASCADE"``
  so the database enforces referential integrity even if the ORM layer is
  bypassed (e.g., via raw SQL or migrations).
- ``file_size`` uses ``BigInteger`` to support files larger than 2 GB.
- ``upload_timestamp`` defaults to the database-server ``now()`` to ensure a
  consistent clock source across distributed application instances.
- ``content_type`` stores MIME types (e.g., ``application/pdf``) for downstream
  processing decisions (parser selection, thumbnail generation).
- An index on ``user_id`` is critical because listing "my documents" is one of
  the most frequent queries.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base_model import BaseModel

if TYPE_CHECKING:
    from backend.app.models.user import User


class Document(BaseModel):
    """
    Represents an uploaded document owned by a User.

    Columns
    -------
    user_id          : Owner's UUID (FK → users.id).
    filename         : Original file name as uploaded by the user.
    file_size        : Size in bytes (BigInteger for large files).
    content_type     : MIME type of the uploaded file.
    upload_timestamp : Server-side UTC timestamp of the upload.
    """

    __tablename__ = "documents"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="FK → users.id — owner of this document.",
    )
    filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Original file name as uploaded by the user.",
    )
    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="File size in bytes.",
    )
    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="MIME type, e.g. application/pdf.",
    )
    upload_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="UTC timestamp of the upload.",
    )

    # ── Relationships ──────────────────────────────────────────────────
    user: Mapped["User"] = relationship(
        "User",
        back_populates="documents",
        lazy="joined",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Document id={self.id} filename={self.filename!r}>"
