"""
backend/app/core/__init__.py
=============================
Makes `core` a Python package and exposes the most commonly imported
objects so callers can do:

    from backend.app.core import settings, get_logger

instead of reaching into sub-modules directly.
"""

from backend.app.core.config import Settings, get_settings, settings
from backend.app.core.logging_config import get_logger, setup_logging

__all__ = [
    "Settings",
    "get_settings",
    "settings",
    "get_logger",
    "setup_logging",
]
