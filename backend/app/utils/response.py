"""
backend/app/utils/response.py
===============================
Standardised API response envelope factory.

Design Decisions:
-----------------
- All API responses share a consistent JSON envelope:
    {
        "success": bool,
        "data": <payload | null>,
        "message": str,
        "meta": { "page": ..., "total": ... }  # optional
    }
  This makes client-side handling predictable: every response has the same
  shape regardless of which endpoint produced it.
- Factory functions (`success_response`, `error_response`, `paginated_response`)
  are thin helpers that return a plain `dict`. FastAPI serialises the dict to
  JSON — no custom response class needed.
- `paginated_response` computes common pagination metadata (`total_pages`,
  `has_next`, `has_previous`) automatically so endpoint code stays clean.
- The helpers are pure functions with no side effects — easy to unit-test.
"""

from __future__ import annotations

import math
from typing import Any, Optional


def success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = 200,
    meta: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Build a successful API response envelope.

    Parameters
    ----------
    data : Any
        The response payload. Can be a dict, list, Pydantic model, or None.
    message : str
        A human-readable success message.
    status_code : int
        HTTP status code (informational only — the actual status is set on
        the `JSONResponse` in the endpoint).
    meta : dict, optional
        Additional metadata (e.g., pagination info).

    Returns
    -------
    dict
        Standard envelope: ``{"success": True, "data": ..., "message": ..., "meta": ...}``

    Example
    -------
        return JSONResponse(
            content=success_response(data=user.model_dump(), message="User created"),
            status_code=201,
        )
    """
    response: dict[str, Any] = {
        "success": True,
        "data": data,
        "message": message,
    }
    if meta is not None:
        response["meta"] = meta
    return response


def error_response(
    message: str = "An error occurred.",
    status_code: int = 500,
    details: Optional[dict[str, Any]] = None,
    error_code: Optional[str] = None,
) -> dict[str, Any]:
    """
    Build an error API response envelope.

    Parameters
    ----------
    message : str
        Human-readable error description.
    status_code : int
        HTTP status code (informational only).
    details : dict, optional
        Machine-readable error details (field errors, service name, etc.)
    error_code : str, optional
        Application-specific error code (e.g., "USER_NOT_FOUND") for
        client-side i18n / programmatic handling.

    Returns
    -------
    dict
        Standard error envelope.
    """
    response: dict[str, Any] = {
        "success": False,
        "data": None,
        "message": message,
    }
    if details:
        response["details"] = details
    if error_code:
        response["error_code"] = error_code
    return response


def paginated_response(
    data: list[Any],
    total: int,
    page: int,
    page_size: int,
    message: str = "Success",
) -> dict[str, Any]:
    """
    Build a paginated API response envelope.

    Automatically computes ``total_pages``, ``has_next``, and ``has_previous``
    from the raw pagination numbers.

    Parameters
    ----------
    data : list
        The current page of items.
    total : int
        Total number of items across all pages.
    page : int
        Current page number (1-indexed).
    page_size : int
        Number of items per page.
    message : str
        Human-readable success message.

    Returns
    -------
    dict
        Standard envelope with a ``meta`` block containing pagination info.

    Example
    -------
        return paginated_response(
            data=[doc.model_dump() for doc in documents],
            total=total_count,
            page=page,
            page_size=page_size,
        )
    """
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0

    return success_response(
        data=data,
        message=message,
        meta={
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
        },
    )
