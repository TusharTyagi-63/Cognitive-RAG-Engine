"""
tests/test_schemas.py
=====================
Tests for Pydantic schemas.
"""
from typing import Dict, Any
import pytest
from pydantic import ValidationError

from backend.app.schemas.user import UserCreate, UserResponse, UserInDB
from backend.app.schemas.document import DocumentCreate, DocumentResponse
from backend.app.schemas.chat import ChatSessionCreate, MessageCreate
from uuid import uuid4

def test_user_create_valid(sample_user_data: Dict[str, Any]):
    user = UserCreate(**sample_user_data)
    assert user.username == "testuser"
    assert user.email == "testuser@example.com"
    assert user.password == "strongpassword123"

def test_user_create_invalid_email(sample_user_data: Dict[str, Any]):
    invalid_data = sample_user_data.copy()
    invalid_data["email"] = "not-an-email"
    with pytest.raises(ValidationError):
        UserCreate(**invalid_data)

def test_user_create_short_password(sample_user_data: Dict[str, Any]):
    invalid_data = sample_user_data.copy()
    invalid_data["password"] = "short"
    with pytest.raises(ValidationError):
        UserCreate(**invalid_data)

def test_chat_session_create_default_title():
    session = ChatSessionCreate()
    assert session.title == "New Chat"

def test_message_create_valid_role():
    msg = MessageCreate(session_id=uuid4(), role="user", content="Hello")
    assert msg.role == "user"

def test_message_create_invalid_role():
    with pytest.raises(ValidationError):
        MessageCreate(session_id=uuid4(), role="alien", content="Hello")
