"""
backend/app/api/v1/endpoints/auth.py
====================================
Authentication and User Registration endpoints.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError

from backend.app.api.dependencies import get_current_user
from backend.app.core.security import create_access_token, create_refresh_token, decode_token
from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.schemas.token import TokenResponse, TokenRefreshRequest
from backend.app.schemas.user import UserCreate, UserResponse
from backend.app.services.user_service import UserService
from backend.app.utils.exceptions import UnauthorizedException
from backend.app.utils.response import success_response

router = APIRouter()

@router.post("/register", summary="Register a new user")
async def register(
    user_in: UserCreate,
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Creates a new user account. Returns the created user profile.
    """
    user = await UserService.create_user(session, user_in)
    await session.commit()
    # Let SQLAlchemy reload the instance from DB properly if needed, though we just committed
    return success_response(data=UserResponse.model_validate(user).model_dump(), message="User registered successfully")


@router.post("/login", response_model=TokenResponse, summary="Login to get JWT tokens")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Authenticates a user via OAuth2 form data (username and password).
    Returns an access token and a refresh token.
    (Note: OAuth2 dictates returning the bare JSON without the success envelope, 
    but since we are returning a Pydantic schema response_model, FastAPI handles it).
    """
    user = await UserService.authenticate(session, form_data.username, form_data.password)
    
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )

@router.post("/refresh", response_model=TokenResponse, summary="Refresh access token")
async def refresh_token(
    refresh_req: TokenRefreshRequest,
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Validates a refresh token and issues a new access/refresh token pair.
    """
    credentials_exception = UnauthorizedException("Could not validate credentials")
    try:
        payload = decode_token(refresh_req.refresh_token)
        user_id_str: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id_str is None or token_type != "refresh":
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    from uuid import UUID
    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise credentials_exception
        
    user = await UserService.get_user_by_id(session, user_id)
    if user is None or not user.is_active:
        raise credentials_exception
        
    new_access_token = create_access_token(subject=user.id)
    new_refresh_token = create_refresh_token(subject=user.id)
    
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer"
    )

@router.get("/me", summary="Get current logged in user")
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Protected route that returns the profile of the currently authenticated user.
    """
    return success_response(data=UserResponse.model_validate(current_user).model_dump())
