"""
backend/app/middleware/logging_middleware.py
=============================================
Request/Response logging middleware with request-ID injection.

Design Decisions:
-----------------
- Built as a Starlette `BaseHTTPMiddleware` subclass so it plugs into FastAPI
  with a single `app.add_middleware()` call.
- A UUID v4 `X-Request-ID` header is generated for every request if the client
  doesn't provide one. This ID is:
    * Stored in the `request_id_var` ContextVar (read by the JSON logger).
    * Echoed back in the response `X-Request-ID` header.
    * Included in every log record emitted during that request.
  This enables end-to-end request tracing through logs and distributed systems.
- Logs **request in** (method, path, client IP) and **response out** (status,
  duration in ms) as structured JSON via the shared logger.
- The middleware catches all exceptions, logs them, then re-raises — ensuring
  the global exception handler in `main.py` still processes them correctly.
- `call_next()` is wrapped in try/finally so `request_id_var` is always reset
  even if an exception is raised mid-request.
"""

from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from backend.app.core.logging_config import get_logger, request_id_var

logger = get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that:
    1. Assigns a unique ``X-Request-ID`` to every HTTP request.
    2. Propagates the ID into the async logging context (``request_id_var``).
    3. Logs request metadata (method, path, IP) when the request arrives.
    4. Logs response metadata (status code, duration in ms) when the response
       is sent.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # ------------------------------------------------------------------
        # 1. Resolve or generate the request ID
        # ------------------------------------------------------------------
        request_id: str = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())

        # Set on the ContextVar so the JSON formatter picks it up automatically
        token = request_id_var.set(request_id)

        start_time = time.perf_counter()

        # ------------------------------------------------------------------
        # 2. Log the incoming request
        # ------------------------------------------------------------------
        logger.info(
            "Request received",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query) or None,
                "client_ip": request.client.host if request.client else "unknown",
                "request_id": request_id,
            },
        )

        # ------------------------------------------------------------------
        # 3. Process the request and capture the response
        # ------------------------------------------------------------------
        response: Response
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "Request failed with unhandled exception",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(exc),
                },
                exc_info=True,
            )
            raise
        finally:
            # Always reset the ContextVar to avoid leaking state between requests
            request_id_var.reset(token)

        # ------------------------------------------------------------------
        # 4. Attach the request ID to the response and log the outcome
        # ------------------------------------------------------------------
        duration_ms = (time.perf_counter() - start_time) * 1000
        response.headers[REQUEST_ID_HEADER] = request_id

        logger.info(
            "Request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "request_id": request_id,
            },
        )

        return response
