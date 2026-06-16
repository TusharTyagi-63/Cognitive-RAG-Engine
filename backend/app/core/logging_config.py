"""
backend/app/core/logging_config.py
===================================
Structured JSON logging configuration for the Cognitive RAG Engine.

Design Decisions:
-----------------
- Uses `python-json-logger` to emit every log record as a single-line JSON
  object — this makes logs trivially parseable by log aggregators (Datadog,
  GCP Cloud Logging, ELK, etc.) without custom parsing rules.
- A custom `ContextFilter` injects request-scoped data (e.g. request_id) via
  Python's `contextvars` — no thread-local hacks, fully async-safe.
- Log level is read from `settings.LOG_LEVEL` so it can be changed per
  environment without code changes.
- The `setup_logging()` function is idempotent: calling it twice is safe.
- `get_logger(name)` is the single factory used by every other module.
  Centralising logger creation means we can add correlation-ID injection or
  sampling in one place later.

Usage
-----
    from backend.app.core.logging_config import get_logger
    logger = get_logger(__name__)
    logger.info("Processing document", extra={"doc_id": "abc-123"})
"""

from __future__ import annotations

import logging
import logging.config
import sys
from contextvars import ContextVar
from typing import Optional

from pythonjsonlogger import jsonlogger  # type: ignore[import-untyped]

from backend.app.core.config import settings

# ---------------------------------------------------------------------------
# Context variable that carries the request-id across async boundaries.
# Set by the logging middleware on every incoming request.
# ---------------------------------------------------------------------------
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class _RequestIdFilter(logging.Filter):
    """
    Injects the current `request_id` into every log record.
    When no request context is active (e.g. startup logs) it logs "-".
    """

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        record.request_id = request_id_var.get() or "-"
        return True


class _CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Extends the default JSON formatter to:
    - Rename `levelname` → `level` for cleaner log schemas.
    - Always include `app`, `version`, and `environment` fields.
    - Move `request_id` to a top-level field.
    """

    def add_fields(
        self,
        log_record: dict,
        record: logging.LogRecord,
        message_dict: dict,
    ) -> None:
        super().add_fields(log_record, record, message_dict)

        # Rename standard fields
        log_record["level"] = log_record.pop("levelname", record.levelname)
        log_record["logger"] = log_record.pop("name", record.name)

        # Static metadata injected into every record
        log_record["app"] = settings.APP_NAME
        log_record["version"] = settings.APP_VERSION
        log_record["environment"] = settings.APP_ENV

        # Request context (set by middleware)
        log_record["request_id"] = getattr(record, "request_id", "-")


def setup_logging() -> None:
    """
    Configure the root logger and all library loggers.
    Call once at application startup (inside `main.py` lifespan).

    The configuration:
    - Formats all records as JSON.
    - Outputs to stdout (container-friendly).
    - Suppresses noisy third-party loggers.
    - Sets the log level from the environment.
    """
    log_level = settings.LOG_LEVEL.upper()

    # Build the JSON formatter
    formatter = _CustomJsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # stdout handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(_RequestIdFilter())

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid duplicate handlers when setup_logging() is called multiple times
    if not root_logger.handlers:
        root_logger.addHandler(console_handler)
    else:
        root_logger.handlers.clear()
        root_logger.addHandler(console_handler)

    # Suppress overly verbose third-party loggers
    for noisy_logger in (
        "uvicorn.access",
        "uvicorn.error",
        "sqlalchemy.engine",
        "sqlalchemy.pool",
        "httpx",
        "httpcore",
    ):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    # Keep SQLAlchemy engine logs at INFO only in DEBUG mode
    if settings.DEBUG:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """
    Factory function to obtain a named logger.

    Every module in the application should obtain its logger via this function
    rather than calling `logging.getLogger()` directly.

    Parameters
    ----------
    name : str
        Typically `__name__` of the calling module.

    Returns
    -------
    logging.Logger
        A logger that automatically inherits the root configuration.

    Example
    -------
        logger = get_logger(__name__)
        logger.info("Server started", extra={"port": 8000})
    """
    return logging.getLogger(name)
