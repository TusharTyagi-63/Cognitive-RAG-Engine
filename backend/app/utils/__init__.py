"""
backend/app/utils/__init__.py
==============================
Utils package — re-exports commonly used helpers.
"""

from backend.app.utils.exceptions import (
    AppException,
    BadRequestException,
    ConflictException,
    DatabaseException,
    ForbiddenException,
    NotFoundException,
    ServiceException,
    UnauthorizedException,
    ValidationException,
)
from backend.app.utils.response import (
    error_response,
    paginated_response,
    success_response,
)

__all__ = [
    # Exceptions
    "AppException",
    "BadRequestException",
    "ConflictException",
    "DatabaseException",
    "ForbiddenException",
    "NotFoundException",
    "ServiceException",
    "UnauthorizedException",
    "ValidationException",
    # Response helpers
    "error_response",
    "paginated_response",
    "success_response",
]
