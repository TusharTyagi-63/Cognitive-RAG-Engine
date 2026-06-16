"""
backend/app/schemas/base.py
=============================
Base Pydantic schema configuration shared across all request/response schemas.

Design Decisions:
-----------------
- `AppBaseModel` centralises the Pydantic `model_config` so every schema in
  the project shares the same behaviour without repeating configuration.
- `from_attributes=True` (formerly `orm_mode`) allows Pydantic to read values
  from SQLAlchemy ORM objects (e.g., `UserResponse.model_validate(user_row)`).
- `populate_by_name=True` allows fields to be populated by their Python name
  even when an `alias` is set — useful for accepting both camelCase API inputs
  and snake_case internal representations.
- UUID and datetime fields are serialised as strings by default (JSON-safe).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AppBaseModel(BaseModel):
    """
    Base class for all Pydantic schemas in the Cognitive RAG Engine.

    All request bodies, response models, and internal DTOs should inherit
    from this class instead of `pydantic.BaseModel` directly.

    Configuration
    -------------
    from_attributes     : Read data from ORM model instances (SQLAlchemy rows).
    populate_by_name    : Allow field population by Python name even if an alias is set.
    str_strip_whitespace: Automatically strip leading/trailing whitespace from strings.
    """

    model_config = ConfigDict(
        from_attributes=True,           # Enables ORM → schema conversion
        populate_by_name=True,          # Accept both alias and field name
        str_strip_whitespace=True,      # Trim accidental whitespace in strings
        json_encoders={
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        },
    )
