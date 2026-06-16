"""
tests/test_documents.py
=======================
Tests for document upload and management.
"""
import io
import pytest
import pytest_asyncio
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
    # Register and login a test user to get a token
    payload = {"username": "docuser", "email": "doc@example.com", "password": "password123"}
    await async_client.post("/api/v1/auth/register", json=payload)
    login_resp = await async_client.post("/api/v1/auth/login", data={"username": "docuser", "password": "password123"})
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_upload_document(async_client: AsyncClient, auth_headers: dict):
    # Mock a text file
    file_content = b"This is a test document."
    files = {"file": ("test.txt", file_content, "text/plain")}
    
    response = await async_client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files=files
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["filename"] == "test.txt"
    assert data["data"]["file_size"] == len(file_content)

@pytest.mark.asyncio
async def test_upload_invalid_extension(async_client: AsyncClient, auth_headers: dict):
    file_content = b"print('hello')"
    files = {"file": ("test.py", file_content, "text/plain")}
    
    response = await async_client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files=files
    )
    
    assert response.status_code == 400
    assert "not allowed" in response.json()["message"]

@pytest.mark.asyncio
async def test_list_documents(async_client: AsyncClient, auth_headers: dict):
    # Upload two files
    files1 = {"file": ("test1.txt", b"content1", "text/plain")}
    await async_client.post("/api/v1/documents/upload", headers=auth_headers, files=files1)
    
    files2 = {"file": ("test2.pdf", b"content2", "application/pdf")}
    await async_client.post("/api/v1/documents/upload", headers=auth_headers, files=files2)
    
    response = await async_client.get("/api/v1/documents/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["documents"]) == 2
    filenames = [item["filename"] for item in data["documents"]]
    assert "test1.txt" in filenames
    assert "test2.pdf" in filenames

@pytest.mark.asyncio
async def test_delete_document(async_client: AsyncClient, auth_headers: dict):
    # Upload a file
    files = {"file": ("test.txt", b"content", "text/plain")}
    upload_resp = await async_client.post("/api/v1/documents/upload", headers=auth_headers, files=files)
    doc_id = upload_resp.json()["data"]["id"]
    
    # Delete it
    del_resp = await async_client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert del_resp.status_code == 200
    
    # Verify it's gone
    list_resp = await async_client.get("/api/v1/documents/", headers=auth_headers)
    assert list_resp.json()["total"] == 0
