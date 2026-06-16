"""
backend/app/services/user_service.py
====================================
Business logic for user registration and authentication.
"""
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import get_password_hash, verify_password
from backend.app.models.user import User
from backend.app.schemas.user import UserCreate
from backend.app.utils.exceptions import BadRequestException, UnauthorizedException

class UserService:
    
    @staticmethod
    async def get_user_by_id(session: AsyncSession, user_id: UUID) -> Optional[User]:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalars().first()
        
    @staticmethod
    async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
        result = await session.execute(select(User).where(User.email == email))
        return result.scalars().first()
        
    @staticmethod
    async def get_user_by_username(session: AsyncSession, username: str) -> Optional[User]:
        result = await session.execute(select(User).where(User.username == username))
        return result.scalars().first()

    @staticmethod
    async def create_user(session: AsyncSession, user_in: UserCreate) -> User:
        """
        Creates a new user, ensuring email and username are unique.
        Hashes the password before storing.
        """
        if await UserService.get_user_by_email(session, user_in.email):
            raise BadRequestException("User with this email already exists.")
            
        if await UserService.get_user_by_username(session, user_in.username):
            raise BadRequestException("User with this username already exists.")
            
        hashed_password = get_password_hash(user_in.password)
        
        user = User(
            username=user_in.username,
            email=user_in.email,
            hashed_password=hashed_password,
            is_active=True,
            is_superuser=False
        )
        
        session.add(user)
        await session.flush()  # To populate user.id immediately
        return user

    @staticmethod
    async def authenticate(session: AsyncSession, username_or_email: str, password: str) -> User:
        """
        Authenticates a user via username OR email.
        Raises UnauthorizedException on failure.
        """
        # Try username first, then email
        user = await UserService.get_user_by_username(session, username_or_email)
        if not user:
            user = await UserService.get_user_by_email(session, username_or_email)
            
        if not user:
            raise UnauthorizedException("Incorrect username or password.")
            
        if not verify_password(password, user.hashed_password):
            raise UnauthorizedException("Incorrect username or password.")
            
        if not user.is_active:
            raise UnauthorizedException("Inactive user account.")
            
        return user
