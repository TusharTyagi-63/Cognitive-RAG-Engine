"""
backend/app/database/__init__.py
==================================
Database package public API.

Re-exports the objects that other layers (models, services, API) need to
import from the database layer, so that import paths stay stable even if
internal module names change.
"""

from backend.app.database.base import Base, TimestampMixin, UUIDMixin
from backend.app.database.connection import async_session_factory, dispose_engine, engine
from backend.app.database.session import DatabaseSessionManager, get_db

__all__ = [
    # Base classes
    "Base",
    "UUIDMixin",
    "TimestampMixin",
    # Engine & factory
    "engine",
    "async_session_factory",
    "dispose_engine",
    # Session helpers
    "get_db",
    "DatabaseSessionManager",
]
