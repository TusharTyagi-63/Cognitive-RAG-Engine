"""
backend/app/models/__init__.py
================================
Model registry — import ALL ORM model classes here.

Why this matters
----------------
Alembic's `env.py` imports `Base` and then calls
`Base.metadata.create_all()` or inspects `Base.metadata` to generate
migration scripts. For Alembic to "see" a table, the corresponding Python
class must have been imported **before** `Base.metadata` is accessed.

By importing every model in this file, a single
    `from backend.app.models import *`
in `alembic/env.py` is enough to register all tables.

Convention
----------
Group imports by domain (auth, documents, pipelines, etc.) and keep them
alphabetically sorted within each group for easy scanning.
"""

# -- Base classes (always first) --
from backend.app.models.base_model import BaseModel  # noqa: F401

# -- Domain models --
from backend.app.models.user import User
from backend.app.models.document import Document
from backend.app.models.chat_session import ChatSession
from backend.app.models.message import Message

__all__ = [
    "BaseModel",
    "User",
    "Document",
    "ChatSession",
    "Message",
]
