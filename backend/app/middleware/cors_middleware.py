"""
backend/app/middleware/cors_middleware.py
==========================================
CORS (Cross-Origin Resource Sharing) configuration helper.

Design Decisions:
-----------------
- CORS is configured using FastAPI's built-in `CORSMiddleware` (Starlette).
- Allowed origins are read from `settings.ALLOWED_ORIGINS` — a list of strings
  that can be overridden per environment via the `.env` file.
- In production (`settings.is_production`), credentials are allowed only if
  the allowed-origins list does not contain the wildcard `"*"` — mixing
  credentials with wildcard origins is rejected by all modern browsers.
- This module exposes a single `configure_cors(app)` function rather than
  subclassing BaseHTTPMiddleware, so `main.py` stays declarative and readable.

Security Notes
--------------
- Never set `allow_origins=["*"]` in production when your frontend sends
  cookies or Authorization headers (`allow_credentials=True`).
- Keep `ALLOWED_ORIGINS` in `.env` — don't hardcode domain names in source.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.logging_config import get_logger

logger = get_logger(__name__)


def configure_cors(app: FastAPI) -> None:
    """
    Add and configure the CORS middleware on the FastAPI application.

    Reads ``settings.ALLOWED_ORIGINS`` to determine which origins to allow.
    In production, enforces that ``allow_credentials`` is not used with
    wildcard origins.

    Parameters
    ----------
    app : FastAPI
        The FastAPI application instance.
    """
    allowed_origins = list(settings.ALLOWED_ORIGINS) if settings.ALLOWED_ORIGINS else []

    # Always ensure the Render frontend is allowed (env var parsing can be flaky)
    render_frontend = "https://cognitive-rag-engine-1.onrender.com"
    if render_frontend not in allowed_origins:
        allowed_origins.append(render_frontend)

    # Fallback to localhost if still empty
    if not allowed_origins:
        logger.warning("ALLOWED_ORIGINS is empty, falling back to localhost")
        allowed_origins = ["http://localhost:3000", "http://localhost:5173", render_frontend]

    # Warn loudly if wildcard is used (it disables credentials support)
    if "*" in allowed_origins:
        logger.warning(
            "CORS is configured with wildcard origin ('*'). "
            "This disables cookie/auth-header support in browsers. "
            "Set specific origins in ALLOWED_ORIGINS for production."
        )

    allow_credentials = "*" not in allowed_origins

    logger.info(
        "Configuring CORS middleware",
        extra={
            "allowed_origins": allowed_origins,
            "allow_credentials": allow_credentials,
        },
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=allow_credentials,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Accept",
            "X-Request-ID",
            "X-Api-Key",
        ],
        expose_headers=["X-Request-ID"],
    )
