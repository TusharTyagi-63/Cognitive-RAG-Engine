"""
backend/app/database/session.py
================================
Database session management and FastAPI dependency injection.

Design Decisions:
-----------------
- `get_db()` is an **async generator** decorated with `@asynccontextmanager`
  semantics implicitly understood by FastAPI's `Depends()`. It yields one
  `AsyncSession` per HTTP request and guarantees cleanup in the `finally` block.
- Commit/rollback is handled here (not in service/endpoint layers) following
  the **Unit of Work pattern**: the session is committed only if the entire
  request handler succeeds; any exception triggers a rollback.
- Services and endpoints receive a typed `AsyncSession` via `Depends(get_db)` —
  they never import `async_session_factory` directly. This keeps business logic
  decoupled from the database infrastructure and makes testing trivial (swap
  `get_db` with a test-scoped session via `app.dependency_overrides`).
- `DatabaseSessionManager` class provides a higher-level context manager for
  use in scripts, background tasks, and Alembic env.py that run outside the
  HTTP request/response cycle.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.connection import async_session_factory
from backend.app.core.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# FastAPI dependency — one session per request
# ---------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session for the duration of
    a single HTTP request.

    Lifecycle
    ---------
    1. A new `AsyncSession` is acquired from the connection pool.
    2. The session is yielded to the endpoint/service.
    3. On success → `commit()` is called automatically.
    4. On any exception → `rollback()` is called to undo partial writes.
    5. `close()` is always called in `finally` to return the connection to
       the pool — even if the response was already streamed to the client.

    Usage
    -----
        from fastapi import Depends
        from sqlalchemy.ext.asyncio import AsyncSession
        from backend.app.database.session import get_db

        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()

    Testing
    -------
        # Override in conftest.py:
        app.dependency_overrides[get_db] = get_test_db
    """
    session: AsyncSession = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# ---------------------------------------------------------------------------
# Standalone session manager — for scripts, background tasks, Alembic
# ---------------------------------------------------------------------------

class DatabaseSessionManager:
    """
    Context-manager-based session provider for use **outside** of HTTP requests.

    Suitable for:
    - Alembic migration scripts
    - CLI commands (e.g., seeding data)
    - Background / scheduled tasks (Celery, APScheduler, etc.)

    Example
    -------
        async with DatabaseSessionManager() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
    """

    def __init__(self) -> None:
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> AsyncSession:
        self._session = async_session_factory()
        return self._session

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._session is None:
            return
        try:
            if exc_type is None:
                await self._session.commit()
            else:
                logger.warning(
                    "Rolling back session due to exception",
                    extra={"exc_type": str(exc_type)},
                )
                await self._session.rollback()
        finally:
            await self._session.close()
            self._session = None
