"""
tests/conftest.py
=================
Global pytest fixtures.
"""

from typing import Dict, Any
import pytest
from backend.app.schemas.user import UserCreate

@pytest.fixture
def sample_user_data() -> Dict[str, Any]:
    return {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "strongpassword123"
    }

@pytest.fixture
def valid_user_create(sample_user_data: Dict[str, Any]) -> UserCreate:
    return UserCreate(**sample_user_data)
