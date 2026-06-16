"""
backend/app/middleware/__init__.py
====================================
Middleware package — exposes configuration helpers.
"""

from backend.app.middleware.cors_middleware import configure_cors
from backend.app.middleware.logging_middleware import RequestLoggingMiddleware

__all__ = [
    "configure_cors",
    "RequestLoggingMiddleware",
]
