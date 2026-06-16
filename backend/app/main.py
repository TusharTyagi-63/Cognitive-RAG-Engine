"""
backend/app/main.py
=====================
FastAPI application entry point for the Cognitive RAG Engine.

This module is responsible for:
1. Bootstrapping the application (logging, configuration).
2. Registering all middleware (CORS, request-ID logging).
3. Mounting versioned API routers.
4. Registering global exception handlers.
5. Managing application lifespan (startup / shutdown hooks).

Design Decisions:
-----------------
- The `lifespan` context manager (introduced in FastAPI 0.93+) replaces the
  deprecated `@app.on_event("startup")` / `@app.on_event("shutdown")` hooks.
  It uses a plain `async with` block — cleaner and more testable.
- All middleware is added via helper functions in the `middleware` package so
  this file stays declarative and easy to read at a glance.
- The global `AppException` handler converts every domain exception into a
  structured JSON error response automatically — endpoint code never needs to
  catch and re-raise.
- FastAPI's built-in `RequestValidationError` handler is overridden to return
  validation errors in the same envelope format as domain errors.
- Swagger UI is enabled in non-production environments only.

Running locally
---------------
    uvicorn backend.app.main:app --reload --port 8000

Running in Docker
-----------------
    docker run -p 8000:8000 --env-file .env rag-backend
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.app.api.v1.router import api_router
from backend.app.core.config import settings
from backend.app.core.logging_config import get_logger, setup_logging
from backend.app.database.connection import dispose_engine
from backend.app.middleware.cors_middleware import configure_cors
from backend.app.middleware.logging_middleware import RequestLoggingMiddleware
from backend.app.utils.exceptions import AppException
from backend.app.utils.response import error_response

# ---------------------------------------------------------------------------
# Bootstrap logging before anything else so the very first log line is
# structured JSON instead of Python's default plaintext format.
# ---------------------------------------------------------------------------
setup_logging()
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — startup and graceful shutdown hooks
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Code BEFORE the ``yield`` runs on startup.
    Code AFTER the ``yield`` runs on shutdown.

    Startup
    -------
    - Log configuration summary.
    - (Future) Warm up the database connection pool.
    - (Future) Initialise ChromaDB client.
    - (Future) Load embedding model.

    Shutdown
    --------
    - Dispose the SQLAlchemy async engine (drains the connection pool).
    - (Future) Flush any pending telemetry.
    """
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info(
        "Starting Cognitive RAG Engine",
        extra={
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
            "debug": settings.DEBUG,
        },
    )
    logger.info(
        "Database configured",
        extra={
            "host": settings.POSTGRES_HOST,
            "port": settings.POSTGRES_PORT,
            "db": settings.POSTGRES_DB,
            "pool_size": settings.DB_POOL_SIZE,
        },
    )

    yield  # ← Application is live and serving requests here

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("Shutting down Cognitive RAG Engine — draining connections…")
    await dispose_engine()
    logger.info("Shutdown complete.")


# ---------------------------------------------------------------------------
# FastAPI application factory
# ---------------------------------------------------------------------------

def create_application() -> FastAPI:
    """
    Application factory.

    Separating construction from the module-level ``app`` variable enables:
    - Isolated instances in tests (call ``create_application()`` per test).
    - Future multi-app setups (e.g., a separate admin sub-app).

    Returns
    -------
    FastAPI
        A fully configured application instance.
    """
    _app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Production-Grade RAG (Retrieval-Augmented Generation) Platform API. "
            "Built with FastAPI, PostgreSQL, SQLAlchemy, and ChromaDB."
        ),
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── Middleware (order matters: outermost is executed first) ───────────────
    # 1. CORS must be first so pre-flight OPTIONS requests are handled before
    #    any other middleware touches the request.
    configure_cors(_app)

    # 2. Request-ID and logging middleware — wraps everything else.
    _app.add_middleware(RequestLoggingMiddleware)

    # ── Routers ───────────────────────────────────────────────────────────────
    _app.include_router(
        api_router,
        prefix=settings.API_V1_PREFIX,  # /api/v1
    )

    # ── Exception Handlers ────────────────────────────────────────────────────
    _register_exception_handlers(_app)

    return _app


def _register_exception_handlers(app: FastAPI) -> None:
    """
    Register global exception handlers on the application.

    These handlers ensure that even unhandled domain exceptions are serialised
    into the standard error envelope format instead of returning a plain 500.
    """

    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request, exc: AppException
    ) -> JSONResponse:
        """
        Converts any ``AppException`` (and its subclasses) into a structured
        JSON error response using the status code baked into the exception.
        """
        logger.warning(
            "Application exception",
            extra={
                "status_code": exc.status_code,
                "error_detail": exc.details,
                "path": request.url.path,
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(
                message=exc.message,
                status_code=exc.status_code,
                details=exc.details if exc.details else None,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """
        Converts Pydantic v2 request-body validation errors into the standard
        error envelope, matching the shape of domain error responses.
        """
        # Extract field-level error details from Pydantic's error list
        field_errors = {
            " → ".join(str(loc) for loc in error["loc"]): error["msg"]
            for error in exc.errors()
        }
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response(
                message="Request validation failed.",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                details={"fields": field_errors},
                error_code="VALIDATION_ERROR",
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """
        Catch-all handler for any exception not caught by more specific handlers.
        Logs the full traceback and returns a generic 500 error to the client.
        """
        logger.error(
            "Unhandled exception",
            extra={"path": request.url.path},
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                message="An internal server error occurred.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code="INTERNAL_SERVER_ERROR",
            ),
        )


# ---------------------------------------------------------------------------
# Module-level application instance
# (imported by Uvicorn: `uvicorn backend.app.main:app`)
# ---------------------------------------------------------------------------
app: FastAPI = create_application()


# ---------------------------------------------------------------------------
# Development entrypoint
# Run directly with: python -m backend.app.main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG,
        log_config=None,  # Disable uvicorn's default logging; we use our own
    )
