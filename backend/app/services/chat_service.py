"""
backend/app/services/chat_service.py
====================================
Service for managing chat sessions and persisting message history in PostgreSQL.
"""
from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.chat_session import ChatSession
from backend.app.models.message import Message
from backend.app.utils.exceptions import NotFoundException

class ChatService:
    @staticmethod
    async def create_session(session: AsyncSession, user_id: UUID, title: str) -> ChatSession:
        """Creates a new chat session."""
        chat_session = ChatSession(user_id=user_id, title=title)
        session.add(chat_session)
        await session.flush()
        return chat_session

    @staticmethod
    async def get_user_sessions(session: AsyncSession, user_id: UUID) -> Sequence[ChatSession]:
        """Fetches all active chat sessions for a user, ordered by most recent."""
        result = await session.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_session_by_id(session: AsyncSession, user_id: UUID, session_id: UUID) -> ChatSession:
        """Fetches a specific chat session, verifying ownership."""
        result = await session.execute(
            select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
        )
        chat_session = result.scalars().first()
        if not chat_session:
            raise NotFoundException("Chat session not found or access denied.")
        return chat_session

    @staticmethod
    async def get_session_history(session: AsyncSession, user_id: UUID, session_id: UUID) -> Sequence[Message]:
        """Fetches all messages in a session chronologically."""
        # First verify the session belongs to the user
        await ChatService.get_session_by_id(session, user_id, session_id)
        
        result = await session.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.timestamp.asc())
        )
        return result.scalars().all()

    @staticmethod
    async def add_message(session: AsyncSession, session_id: UUID, role: str, content: str) -> Message:
        """Persists a single message to the database."""
        msg = Message(session_id=session_id, role=role, content=content)
        session.add(msg)
        await session.flush()
        
        # Touch the session's updated_at timestamp so it bubbles up in lists
        result = await session.execute(select(ChatSession).where(ChatSession.id == session_id))
        chat_session = result.scalars().first()
        if chat_session:
            # SQLAlchemy automatically updates the updated_at column on modification
            chat_session.title = chat_session.title 
            
        return msg

    @staticmethod
    async def delete_session(session: AsyncSession, user_id: UUID, session_id: UUID) -> None:
        """Deletes a chat session (messages are cascade deleted by DB)."""
        chat_session = await ChatService.get_session_by_id(session, user_id, session_id)
        await session.delete(chat_session)
