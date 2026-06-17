"""
backend/app/database/connection.py
====================================
Async SQLAlchemy engine and connection pool configuration.

Design Decisions:
-----------------
- Uses `create_async_engine` (SQLAlchemy 2.x) with the `asyncpg` dialect for
  fully non-blocking database I/O — critical for a FastAPI async application.
- All pool parameters are read from `settings` so they can be tuned per
  environment without code changes.
- `pool_pre_ping=True` ensures stale connections (e.g., after a Postgres
  restart) are detected and replaced before being handed to the application.
- `echo=settings.DEBUG` logs all SQL statements in development for debugging,
  but stays silent in staging/production.
- `engine` and `async_session_factory` are module-level singletons — created
  once at import time. This is safe because SQLAlchemy engines are thread/task
  safe by design.
- `dispose_engine()` is called during application shutdown to drain the pool
  gracefully, preventing dangling connections.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.core.config import settings
from backend.app.core.logging_config import get_logger

logger = get_logger(__name__)


def _build_engine() -> AsyncEngine:
    """
    Build and return the async SQLAlchemy engine.

    Pool settings
    -------------
    pool_size      : Number of persistent connections maintained in the pool.
    max_overflow   : Extra connections allowed when pool_size is exhausted.
    pool_timeout   : Seconds to wait for a connection before raising an error.
    pool_pre_ping  : Sends a lightweight SELECT 1 before each checkout to
                     detect and recycle dead connections automatically.
    pool_recycle   : Recycles connections older than N seconds — prevents
                     PostgreSQL from closing idle connections server-side.
    """
    logger.info(
        "Creating async database engine",
        extra={
            "host": settings.POSTGRES_HOST,
            "port": settings.POSTGRES_PORT,
            "db": settings.POSTGRES_DB,
            "pool_size": settings.DB_POOL_SIZE,
        },
    )

    connect_kwargs: dict = {
        # asyncpg-specific: command_timeout prevents long-running queries
        # from blocking the event loop indefinitely.
        "command_timeout": 60,
        "server_settings": {
            "application_name": settings.APP_NAME,
        },
        # Required for Supabase PgBouncer / Transaction Pooler compatibility
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    }

    # Supabase and most cloud Postgres providers require SSL
    if settings.is_production:
        import ssl as _ssl
        ssl_ctx = _ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = _ssl.CERT_NONE
        connect_kwargs["ssl"] = ssl_ctx

    return create_async_engine(
        url=settings.DATABASE_URL,
        echo=settings.DEBUG,                    # SQL statement logging
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_pre_ping=True,
        pool_recycle=3600,                      # Recycle connections hourly
        connect_args=connect_kwargs,
    )


# ---------------------------------------------------------------------------
# Module-level singletons (created once, reused for the application lifetime)
# ---------------------------------------------------------------------------

#: The async SQLAlchemy engine — manages the connection pool.
engine: AsyncEngine = _build_engine()

#: Async session factory — call `async_session_factory()` to get a session.
#: `expire_on_commit=False` prevents lazy-loading after commit (safe with async).
async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def dispose_engine() -> None:
    """
    Gracefully close all connections in the pool.

    Call this during application shutdown (inside the lifespan context manager
    in main.py) to ensure all database connections are properly released before
    the process exits.
    """
    logger.info("Disposing database engine and closing connection pool.")
    await engine.dispose()
