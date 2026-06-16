"""
backend/app/api/dependencies.py
===============================
FastAPI dependencies for route protection and data injection.
"""
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import decode_token
from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.services.user_service import UserService
from backend.app.utils.exceptions import UnauthorizedException

# OAuth2PasswordBearer expects a token URL to instruct Swagger UI where to get the token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    """
    Dependency that decodes the JWT and returns the current User.
    Raises 401 Unauthorized if token is invalid, expired, or user doesn't exist.
    """
    credentials_exception = UnauthorizedException("Could not validate credentials")
    
    try:
        payload = decode_token(token)
        user_id_str: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id_str is None or token_type != "access":
            raise credentials_exception
            
        try:
            user_id = UUID(user_id_str)
        except ValueError:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
        
    user = await UserService.get_user_by_id(session, user_id)
    if user is None:
        raise credentials_exception
        
    if not user.is_active:
        raise UnauthorizedException("Inactive user account")
        
    return user
