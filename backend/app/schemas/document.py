"""
backend/app/schemas/document.py
================================
Pydantic schemas for Document-related request/response payloads.

Design Decisions:
-----------------
- **DocumentCreate** requires all four mandatory fields (filename, file_size,
  content_type, user_id). ``file_size`` is validated to be positive.
- **DocumentResponse** exposes every column including server-generated
  ``upload_timestamp`` and inherited ``created_at`` / ``updated_at``.
- **DocumentListResponse** wraps a list of ``DocumentResponse`` plus a
  ``total`` count — ready-made for paginated list endpoints.
- ``content_type`` is validated against a simple pattern to ensure it looks
  like a MIME type (``type/subtype``).
"""

from __future__ import annotations

from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import Field, field_validator

from backend.app.schemas.base import AppBaseModel


class DocumentCreate(AppBaseModel):
    """Schema for document upload metadata."""

    filename: str = Field(
        ...,
        max_length=500,
        description="Original filename as uploaded by the user.",
        examples=["research_paper.pdf"],
    )
    file_size: int = Field(
        ...,
        gt=0,
        description="File size in bytes (must be positive).",
        examples=[1048576],
    )
    content_type: str = Field(
        ...,
        max_length=100,
        description="MIME type of the file.",
        examples=["application/pdf"],
    )
    user_id: UUID = Field(
        ...,
        description="UUID of the owning user.",
    )

    @field_validator("content_type")
    @classmethod
    def content_type_must_be_mime(cls, v: str) -> str:
        """Ensure the content_type looks like a valid MIME type (type/subtype)."""
        if "/" not in v:
            raise ValueError(
                "content_type must be a valid MIME type (e.g. 'application/pdf')."
            )
        return v


class DocumentResponse(AppBaseModel):
    """Full document representation returned by API endpoints."""

    id: UUID
    user_id: UUID
    filename: str
    file_size: int
    content_type: str
    upload_timestamp: datetime
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(AppBaseModel):
    """Paginated list of documents."""

    total: int = Field(..., description="Total number of documents matching the query.")
    documents: List[DocumentResponse] = Field(
        ...,
        description="List of document records.",
    )
