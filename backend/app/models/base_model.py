"""
backend/app/models/base_model.py
==================================
Abstract base model combining UUID primary key and timestamp columns.

Design Decisions:
-----------------
- `BaseModel` combines `Base`, `UUIDMixin`, and `TimestampMixin` into a single
  class that most real-world ORM models will inherit from.
- It is marked `__abstract__ = True` so SQLAlchemy does NOT create a
  corresponding table for it — it purely donates columns to subclasses.
- The `__repr__` is defined here once so every model gets a useful string
  representation for debugging (e.g. in logs and the interactive shell).

Usage
-----
    class Document(BaseModel):
        __tablename__ = "documents"

        title: Mapped[str] = mapped_column(String(500), nullable=False)
        # inherits: id, created_at, updated_at automatically
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import declared_attr

from backend.app.database.base import Base, TimestampMixin, UUIDMixin


class BaseModel(UUIDMixin, TimestampMixin, Base):
    """
    Concrete abstract base that every ORM model should inherit from.

    Inherited columns
    -----------------
    id          : UUID primary key (generated client-side)
    created_at  : UTC timestamp, set on INSERT
    updated_at  : UTC timestamp, refreshed on UPDATE
    """

    __abstract__ = True

    @declared_attr.directive
    def __tablename__(cls) -> str:  # noqa: N805
        """
        Auto-generate the table name from the class name (snake_case plural).

        Examples
        --------
        User        → users
        Document    → documents
        RagPipeline → rag_pipelines

        Override in the subclass if you need a different name:
            __tablename__ = "my_custom_table"
        """
        import re
        # Insert underscore before uppercase letters, lower-case, then pluralise
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()
        return f"{name}s"

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{self.__class__.__name__} id={self.id}>"

    def to_dict(self) -> dict:
        """
        Return a dictionary of column values (excludes relationships).
        Useful for logging and debugging — not intended as a serialization path
        (use Pydantic schemas for that).
        """
        return {
            col.key: getattr(self, col.key)
            for col in self.__table__.columns  # type: ignore[attr-defined]
        }
