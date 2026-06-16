"""
backend/app/schemas/token.py
============================
Pydantic schemas for authentication tokens.
"""
from backend.app.schemas.base import AppBaseModel

class TokenResponse(AppBaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenRefreshRequest(AppBaseModel):
    refresh_token: str
