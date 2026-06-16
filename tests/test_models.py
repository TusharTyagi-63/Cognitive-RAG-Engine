"""
tests/test_models.py
====================
Tests for ORM models.
"""
from backend.app.models.user import User
from backend.app.models.document import Document
from backend.app.models.chat_session import ChatSession
from backend.app.models.message import Message

def test_user_creation():
    user = User(username="test_user", email="test@example.com", hashed_password="hashed", is_active=True, is_superuser=False)
    assert user.username == "test_user"
    assert user.email == "test@example.com"
    assert user.is_active is True
    assert user.is_superuser is False

def test_document_creation():
    doc = Document(filename="test.pdf", file_size=1024, content_type="application/pdf")
    assert doc.filename == "test.pdf"
    assert doc.file_size == 1024
    assert doc.content_type == "application/pdf"

def test_chat_session_creation():
    session = ChatSession(title="My Session")
    assert session.title == "My Session"

def test_message_creation():
    msg = Message(role="user", content="Hello world")
    assert msg.role == "user"
    assert msg.content == "Hello world"
