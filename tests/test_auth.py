"""
tests/test_auth.py
==================
Tests for authentication endpoints.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.main import app
from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.core.security import get_password_hash

from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from backend.app.database.base import Base

# Create engine ONCE for all requests in the tests so they share the DB
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

import pytest_asyncio

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    # Drop and recreate all tables for each test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield

@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client

@pytest.fixture
def test_user_payload():
    return {
        "username": "authuser",
        "email": "auth@example.com",
        "password": "authpassword123"
    }

@pytest.mark.asyncio
async def test_register_user(async_client: AsyncClient, test_user_payload: dict):
    response = await async_client.post("/api/v1/auth/register", json=test_user_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["username"] == "authuser"
    assert data["data"]["email"] == "auth@example.com"
    assert "hashed_password" not in data["data"]
    assert "password" not in data["data"]

@pytest.mark.asyncio
async def test_register_duplicate_user(async_client: AsyncClient, test_user_payload: dict):
    await async_client.post("/api/v1/auth/register", json=test_user_payload)
    response = await async_client.post("/api/v1/auth/register", json=test_user_payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["message"]

@pytest.mark.asyncio
async def test_login_user(async_client: AsyncClient, test_user_payload: dict):
    # First register the user
    await async_client.post("/api/v1/auth/register", json=test_user_payload)
    
    # Then login
    response = await async_client.post(
        "/api/v1/auth/login", 
        data={"username": "authuser", "password": "authpassword123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_invalid_password(async_client: AsyncClient, test_user_payload: dict):
    await async_client.post("/api/v1/auth/register", json=test_user_payload)
    
    response = await async_client.post(
        "/api/v1/auth/login", 
        data={"username": "authuser", "password": "wrongpassword"}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_refresh_token(async_client: AsyncClient, test_user_payload: dict):
    await async_client.post("/api/v1/auth/register", json=test_user_payload)
    login_response = await async_client.post(
        "/api/v1/auth/login", 
        data={"username": "authuser", "password": "authpassword123"}
    )
    refresh_token = login_response.json()["refresh_token"]
    
    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()

@pytest.mark.asyncio
async def test_get_me(async_client: AsyncClient, test_user_payload: dict):
    await async_client.post("/api/v1/auth/register", json=test_user_payload)
    login_response = await async_client.post(
        "/api/v1/auth/login", 
        data={"username": "authuser", "password": "authpassword123"}
    )
    access_token = login_response.json()["access_token"]
    
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert response.json()["data"]["username"] == "authuser"

@pytest.mark.asyncio
async def test_get_me_no_token(async_client: AsyncClient):
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401
