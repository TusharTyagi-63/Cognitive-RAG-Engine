"""
backend/app/schemas/__init__.py
================================
Schemas package — re-exports all public schema types for clean imports.
"""

from backend.app.schemas.base import AppBaseModel
from backend.app.schemas.health import (
    DatabaseStatus,
    HealthDataSchema,
    HealthResponse,
    ServiceStatus,
)
from backend.app.schemas.user import UserCreate, UserUpdate, UserResponse, UserInDB
from backend.app.schemas.document import DocumentCreate, DocumentResponse, DocumentListResponse
from backend.app.schemas.chat import ChatSessionCreate, ChatSessionResponse, MessageCreate, MessageResponse, ChatHistoryResponse
from backend.app.schemas.token import TokenResponse, TokenRefreshRequest

__all__ = [
    "AppBaseModel",
    "DatabaseStatus",
    "HealthDataSchema",
    "HealthResponse",
    "ServiceStatus",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserInDB",
    "DocumentCreate",
    "DocumentResponse",
    "DocumentListResponse",
    "ChatSessionCreate",
    "ChatSessionResponse",
    "MessageCreate",
    "MessageResponse",
    "ChatHistoryResponse",
    "TokenResponse",
    "TokenRefreshRequest",
]
