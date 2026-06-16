"""
backend/app/schemas/user.py
============================
Pydantic schemas for User-related request/response payloads.

Design Decisions:
-----------------
- **UserCreate** validates username length (3-50), email format via
  ``EmailStr``, and password length (8-128) at the schema boundary so invalid
  data never reaches the service layer.
- **UserUpdate** makes every field ``Optional`` so clients can PATCH individual
  fields without resending the full resource.
- **UserResponse** deliberately omits ``hashed_password`` — this schema is the
  *only* shape that should ever be serialized to an external client.
- **UserInDB** extends ``UserResponse`` with ``hashed_password`` for internal
  use only (e.g., password-verification logic in the auth service).
- Field validators use ``@field_validator`` (Pydantic v2 API) to keep
  validation co-located with the schema definition.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from backend.app.schemas.base import AppBaseModel


class UserCreate(AppBaseModel):
    """Schema for user registration requests."""

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Unique display name (3-50 characters).",
        examples=["john_doe"],
    )
    email: EmailStr = Field(
        ...,
        description="Valid e-mail address.",
        examples=["john@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Plain-text password (8-128 characters). Will be hashed before storage.",
        examples=["S3cureP@ss!"],
    )

    @field_validator("username")
    @classmethod
    def username_must_be_alphanumeric(cls, v: str) -> str:
        """Allow only letters, digits, underscores, and hyphens."""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Username may only contain letters, digits, underscores, and hyphens."
            )
        return v

    @field_validator("password")
    @classmethod
    def password_must_not_be_common(cls, v: str) -> str:
        """Basic check — reject trivially weak passwords."""
        trivial = {"password", "12345678", "qwertyui"}
        if v.lower() in trivial:
            raise ValueError("This password is too common. Choose a stronger one.")
        return v


class UserUpdate(AppBaseModel):
    """Schema for partial user updates (PATCH)."""

    username: Optional[str] = Field(
        None,
        min_length=3,
        max_length=50,
        description="New display name.",
    )
    email: Optional[EmailStr] = Field(
        None,
        description="New e-mail address.",
    )
    password: Optional[str] = Field(
        None,
        min_length=8,
        max_length=128,
        description="New plain-text password.",
    )
    is_active: Optional[bool] = Field(
        None,
        description="Enable or disable the account.",
    )
    is_superuser: Optional[bool] = Field(
        None,
        description="Grant or revoke admin privileges.",
    )


class UserResponse(AppBaseModel):
    """
    Public user representation returned by API endpoints.

    **Never** includes ``hashed_password``.
    """

    id: UUID
    username: str
    email: EmailStr
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime


class UserInDB(UserResponse):
    """
    Internal-only schema that extends ``UserResponse`` with the password hash.

    Used exclusively inside the authentication / service layer — never
    serialized to an API response.
    """

    hashed_password: str
