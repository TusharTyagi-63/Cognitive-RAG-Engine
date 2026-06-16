"""
backend/app/api/v1/router.py
==============================
API v1 router — aggregates all v1 endpoint routers.

Design Decisions:
-----------------
- All v1 endpoints are included here with their resource-specific prefixes and
  tags. `main.py` only needs to know about this single router.
- Using an `APIRouter` (not the app directly) keeps the v1 surface area
  contained and allows the entire v1 API to be mounted with a single prefix
  (`/api/v1`) in `main.py`.
- As new endpoint modules are created (users, documents, pipelines), they are
  registered here — never directly in `main.py`. This follows the
  Open/Closed Principle: `main.py` is closed for modification, the router is
  open for extension.

Adding a new resource
---------------------
1. Create `backend/app/api/v1/endpoints/<resource>.py`
2. Import its `router` here and add an `api_router.include_router(...)` line.
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.v1.endpoints.health import router as health_router
from backend.app.api.v1.endpoints.auth import router as auth_router
from backend.app.api.v1.endpoints.documents import router as documents_router
from backend.app.api.v1.endpoints.chat import router as chat_router

# ── v1 aggregate router ───────────────────────────────────────────────────────
api_router = APIRouter()

# Monitoring
api_router.include_router(
    health_router,
    prefix="",          # Results in /api/v1/health (prefix set in main.py)
    tags=["Monitoring"],
)

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(documents_router, prefix="/documents", tags=["Documents"])
api_router.include_router(chat_router, prefix="/chat", tags=["Chat"])

# Future routers (uncomment as they are implemented):
# from backend.app.api.v1.endpoints.users     import router as users_router
# from backend.app.api.v1.endpoints.documents import router as documents_router
# from backend.app.api.v1.endpoints.pipelines import router as pipelines_router

# api_router.include_router(users_router,     prefix="/users",     tags=["Users"])
# api_router.include_router(documents_router, prefix="/documents", tags=["Documents"])
# api_router.include_router(pipelines_router, prefix="/pipelines", tags=["Pipelines"])
