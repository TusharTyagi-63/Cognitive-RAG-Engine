"""
tests/test_chat.py
==================
Tests for Chat System CRUD and Message generation.
"""
import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.database.session import get_db
from backend.app.database.base import Base

from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# Setup shared in-memory sqlite DB for tests
test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False
)
test_session_maker = async_sessionmaker(bind=test_engine, expire_on_commit=False)

async def override_get_db():
    async with test_session_maker() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield

@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client

@pytest_asyncio.fixture
async def auth_headers(async_client: AsyncClient):
    payload = {"username": "chatuser", "email": "chat@example.com", "password": "password123"}
    await async_client.post("/api/v1/auth/register", json=payload)
    login_resp = await async_client.post("/api/v1/auth/login", data={"username": "chatuser", "password": "password123"})
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_create_and_list_sessions(async_client: AsyncClient, auth_headers: dict):
    # Create session
    resp1 = await async_client.post("/api/v1/chat/sessions", headers=auth_headers, json={"title": "Physics Chat"})
    assert resp1.status_code == 200
    session_id = resp1.json()["data"]["id"]
    
    # List sessions
    resp2 = await async_client.get("/api/v1/chat/sessions", headers=auth_headers)
    assert resp2.status_code == 200
    sessions = resp2.json()["data"]
    assert len(sessions) == 1
    assert sessions[0]["title"] == "Physics Chat"
    assert sessions[0]["id"] == session_id

@pytest.mark.asyncio
async def test_send_message_and_history(async_client: AsyncClient, auth_headers: dict):
    # Create session
    resp = await async_client.post("/api/v1/chat/sessions", headers=auth_headers, json={"title": "Test Chat"})
    session_id = resp.json()["data"]["id"]
    
    # Mock RAG Service
    with patch('backend.app.api.v1.endpoints.chat.RAGService.query', new_callable=AsyncMock) as mock_query:
        mock_query.return_value = {
            "answer": "This is a mocked AI response.",
            "sources": []
        }
        
        # Send a message
        msg_resp = await async_client.post(
            f"/api/v1/chat/sessions/{session_id}/message", 
            headers=auth_headers, 
            json={"content": "Hello AI"}
        )
        assert msg_resp.status_code == 200
        ai_msg = msg_resp.json()["data"]
        assert ai_msg["role"] == "assistant"
        assert ai_msg["content"] == "This is a mocked AI response."
        
        mock_query.assert_called_once()
        
    # Get History
    hist_resp = await async_client.get(f"/api/v1/chat/sessions/{session_id}/messages", headers=auth_headers)
    assert hist_resp.status_code == 200
    
    history_data = hist_resp.json()["data"]
    assert history_data["session"]["id"] == session_id
    messages = history_data["messages"]
    
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello AI"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "This is a mocked AI response."
