"""
backend/app/api/v1/endpoints/health.py
========================================
Health-check endpoint.

Design Decisions:
-----------------
- `GET /api/v1/health` is the canonical liveness + readiness probe endpoint.
  Load balancers, Kubernetes probes, and monitoring dashboards all target it.
- The endpoint actively verifies the database connection (not just that the
  process is running) by opening a raw async connection via the engine and
  executing `SELECT 1`. This intentionally bypasses the normal `get_db`
  dependency so that:
    * A missing/unreachable DB never raises an uncaught exception.
    * The response body reflects `"database": "unreachable"` with HTTP 200 —
      meaning the service is alive even if the DB is temporarily down.
    * Load balancers keep routing traffic to the pod; an ops alert fires
      separately when `data.database == "unreachable"`.
- `uptime_seconds` is tracked via a module-level `_start_time` set at import,
  giving a lightweight approximation of worker uptime.
"""

from __future__ import annotations

import time

from fastapi import APIRouter
from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.core.logging_config import get_logger
from backend.app.database.connection import engine
from backend.app.schemas.health import (
    DatabaseStatus,
    HealthDataSchema,
    HealthResponse,
    ServiceStatus,
)
from backend.app.utils.response import success_response

logger = get_logger(__name__)

router = APIRouter()

# Track the time this worker module was loaded (approximates uptime)
_start_time: float = time.monotonic()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service Health Check",
    description=(
        "Returns the health status of the Cognitive RAG Engine service and its dependencies. "
        "Use this endpoint for liveness/readiness probes."
    ),
    tags=["Monitoring"],
)
async def health_check() -> dict:
    """
    Liveness + readiness health-check endpoint.

    Checks
    ------
    - Application process is alive.
    - Database connection can be established and a query executed.

    Returns
    -------
    200 OK
        Always returns 200. The ``data.status`` field indicates overall health:
        - ``healthy``  : All systems operational.
        - ``degraded`` : Application running but one or more dependencies are down.
    """
    uptime = time.monotonic() - _start_time

    # ------------------------------------------------------------------
    # Database probe — lightweight raw connection, bypasses get_db so
    # an unreachable DB degrades gracefully instead of raising 500.
    # ------------------------------------------------------------------
    db_status: DatabaseStatus
    overall_status: ServiceStatus

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = DatabaseStatus.CONNECTED
        overall_status = ServiceStatus.HEALTHY
        logger.debug("Health check: database connection OK")
    except Exception as exc:
        logger.warning(
            "Health check: database connection failed",
            extra={"error": str(exc)},
        )
        db_status = f"unreachable: {str(exc)}"
        overall_status = ServiceStatus.DEGRADED

    # ------------------------------------------------------------------
    # Assemble and return the response
    # ------------------------------------------------------------------
    health_data = HealthDataSchema(
        status=overall_status,
        database=db_status,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        uptime_seconds=round(uptime, 2),
    )

    logger.info(
        "Health check completed",
        extra={
            "status": overall_status.value,
            "database": db_status.value,
            "uptime_seconds": health_data.uptime_seconds,
        },
    )

    return success_response(
        data=health_data.model_dump(),
        message="Service is running",
    )
