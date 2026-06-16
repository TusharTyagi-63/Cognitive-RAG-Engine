"""
backend/app/core/config.py
==========================
Central application configuration module.

Design Decisions:
-----------------
- Uses Pydantic v2 `BaseSettings` so every setting is:
    * Loaded from the environment / .env file automatically
    * Type-validated at startup (bad config fails fast, not at runtime)
    * IDE-friendly (full autocomplete)
- The `@lru_cache` on `get_settings()` means the class is instantiated ONCE
  and the same object is returned to every caller — effectively a singleton
  without any global state anti-pattern.
- DATABASE_URL is computed as a `@computed_field` from the individual Postgres
  fields so callers never have to assemble the URL themselves, but the raw
  fields are still override-able independently.
- Follows the Open/Closed Principle: adding a new setting means adding one line,
  not modifying any caller.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All application settings, loaded from environment variables or .env file.

    Sections
    --------
    Application  : basic metadata and runtime flags
    API          : routing and CORS
    Database     : PostgreSQL connection parameters and pool configuration
    Security     : JWT secrets and token lifetimes
    """

    # Document Management
    UPLOAD_DIR: str = "backend/data/uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS: list[str] = [".txt", ".pdf", ".md", ".csv"]

    # Vector Database
    QDRANT_DB_DIR: str = "backend/data/qdrant"
    QDRANT_COLLECTION_NAME: str = "rag_documents"
    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str | None = None

    # LLM Settings
    OPENAI_API_KEY: str = "dummy_key_for_now" # Should be set in .env
    OPENAI_BASE_URL: str | None = None        # e.g., "http://localhost:11434/v1" for Ollama
    LLM_MODEL: str = "gpt-3.5-turbo"          # e.g., "llama3" for Ollama

    model_config = SettingsConfigDict(
        env_file=".env",            # Looks for .env relative to process cwd
        env_file_encoding="utf-8",
        case_sensitive=False,       # APP_NAME and app_name are equivalent
        extra="ignore",             # Ignore unknown env vars silently
    )

    # --------------------------------------------------------------------------
    # Application
    # --------------------------------------------------------------------------
    APP_NAME: str = "Cognitive RAG Engine"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"    # development | staging | production
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # --------------------------------------------------------------------------
    # API
    # --------------------------------------------------------------------------
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # --------------------------------------------------------------------------
    # Database — individual fields (used to build the connection URL)
    # --------------------------------------------------------------------------
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "rag_platform"
    POSTGRES_USER: str = "rag_user"
    POSTGRES_PASSWORD: str = "rag_password"

    # Pool settings
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        """
        Async PostgreSQL DSN assembled from individual fields.
        Uses the `postgresql+asyncpg` dialect for SQLAlchemy async engine.
        """
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SYNC_DATABASE_URL(self) -> str:
        """
        Sync DSN for Alembic migrations (Alembic does not support asyncpg directly).
        """
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # --------------------------------------------------------------------------
    # Security / JWT
    # --------------------------------------------------------------------------
    SECRET_KEY: str = "change-me-to-a-long-random-string-at-least-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --------------------------------------------------------------------------
    # Convenience helpers
    # --------------------------------------------------------------------------
    @property
    def is_production(self) -> bool:
        """True when running in the production environment."""
        return self.APP_ENV.lower() == "production"

    @property
    def is_development(self) -> bool:
        """True when running in the development environment."""
        return self.APP_ENV.lower() == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns the cached Settings singleton.

    Usage (anywhere in the app)
    ---------------------------
    from backend.app.core.config import get_settings
    settings = get_settings()

    Usage as a FastAPI dependency
    -----------------------------
    from fastapi import Depends
    from backend.app.core.config import Settings, get_settings

    def some_endpoint(settings: Settings = Depends(get_settings)):
        ...
    """
    return Settings()


# Module-level shortcut for non-DI usage (e.g., logging setup at import time)
settings: Settings = get_settings()
