"""
backend/app/schemas/health.py
===============================
Pydantic schemas for the health-check endpoint.

Design Decisions:
-----------------
- `DatabaseStatus` and `ServiceStatus` are string enums that constrain the
  allowed values — prevents typos like "healty" from leaking into responses.
- `HealthDataSchema` carries the detailed status of each sub-system so API
  consumers (monitoring dashboards, load-balancer checks) can distinguish a
  total outage from a partial degradation.
- `HealthResponse` wraps the data in the standard API envelope defined in
  `utils/response.py` — kept as a standalone schema here for Swagger docs.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from backend.app.schemas.base import AppBaseModel


class ServiceStatus(str, Enum):
    """Overall service health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class DatabaseStatus(str, Enum):
    """Database connectivity status."""
    CONNECTED = "connected"
    UNREACHABLE = "unreachable"


class HealthDataSchema(AppBaseModel):
    """
    Detailed health information for the service and its dependencies.

    Fields
    ------
    status      : Overall health of the service.
    database    : Whether the PostgreSQL connection is alive.
    version     : Application version (from settings).
    environment : Current runtime environment (development/staging/production).
    """
    status: ServiceStatus
    database: str
    version: str
    environment: str
    uptime_seconds: Optional[float] = None


class HealthResponse(AppBaseModel):
    """
    Standard API envelope wrapping the health-check payload.

    This mirrors the shape returned by `utils/response.py` but is defined
    explicitly here so FastAPI/Swagger generates an accurate response schema.
    """
    success: bool
    data: HealthDataSchema
    message: str
