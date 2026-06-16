"""
backend/app/utils/exceptions.py
================================
Custom exception hierarchy for the Cognitive RAG Engine.

Design Decisions:
-----------------
- `AppException` is the root of the hierarchy. Every domain-specific exception
  extends it so callers can catch either a specific type or the broad base.
- Each exception carries an HTTP status code, a human-readable message, and
  an optional `details` dict for machine-readable context (useful in logging
  and structured error responses).
- The global exception handler in `main.py` catches `AppException` (and any
  subclass) and converts it to a JSON response using the status code and message
  defined on the exception — no try/except boilerplate in endpoint code.
- Keeping HTTP codes on the exceptions (rather than in endpoint handlers)
  satisfies the Single Responsibility Principle: the exception knows the right
  HTTP status; the handler just serialises it.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import status


class AppException(Exception):
    """
    Base exception for all application-level errors.

    Parameters
    ----------
    message : str
        Human-readable error message returned in the API response.
    status_code : int
        HTTP status code. Defaults to 500 Internal Server Error.
    details : dict, optional
        Additional structured data (field names, error codes, etc.)
        included in the response body under `"details"`.
    """

    def __init__(
        self,
        message: str = "An unexpected error occurred.",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"{self.__class__.__name__}("
            f"status_code={self.status_code}, "
            f"message={self.message!r})"
        )


# ---------------------------------------------------------------------------
# HTTP 400 — Bad Request
# ---------------------------------------------------------------------------

class ValidationException(AppException):
    """Raised when request data fails business-rule validation."""

    def __init__(
        self,
        message: str = "Validation failed.",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class BadRequestException(AppException):
    """Raised when the request is malformed or cannot be processed as-is."""

    def __init__(
        self,
        message: str = "Bad request.",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


# ---------------------------------------------------------------------------
# HTTP 401 / 403 — Authentication & Authorisation
# ---------------------------------------------------------------------------

class UnauthorizedException(AppException):
    """Raised when the request lacks valid authentication credentials."""

    def __init__(self, message: str = "Authentication required.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class ForbiddenException(AppException):
    """Raised when the authenticated user lacks permission for the action."""

    def __init__(self, message: str = "You do not have permission to perform this action.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


# ---------------------------------------------------------------------------
# HTTP 404 — Not Found
# ---------------------------------------------------------------------------

class NotFoundException(AppException):
    """Raised when a requested resource does not exist."""

    def __init__(
        self,
        resource: str = "Resource",
        identifier: Optional[Any] = None,
    ) -> None:
        message = (
            f"{resource} not found."
            if identifier is None
            else f"{resource} with id '{identifier}' not found."
        )
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "identifier": str(identifier) if identifier else None},
        )


# ---------------------------------------------------------------------------
# HTTP 409 — Conflict
# ---------------------------------------------------------------------------

class ConflictException(AppException):
    """Raised when an operation conflicts with the current state (e.g., duplicate)."""

    def __init__(
        self,
        message: str = "A conflict occurred.",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


# ---------------------------------------------------------------------------
# HTTP 500 — Internal Server / Database Errors
# ---------------------------------------------------------------------------

class DatabaseException(AppException):
    """Raised when a database operation fails unexpectedly."""

    def __init__(
        self,
        message: str = "A database error occurred.",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class ServiceException(AppException):
    """Raised when an internal service (e.g., LLM, vector store) fails."""

    def __init__(
        self,
        service: str = "Internal service",
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message or f"{service} encountered an error.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"service": service, **(details or {})},
        )
