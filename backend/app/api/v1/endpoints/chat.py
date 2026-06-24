"""
backend/app/api/v1/endpoints/chat.py
====================================
Endpoints for interacting with the conversational AI and viewing history.
"""
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user
from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.schemas.chat import (
    ChatSessionCreate, 
    ChatSessionResponse, 
    MessageCreate, 
    MessageResponse, 
    ChatHistoryResponse
)
from backend.app.services.chat_service import ChatService
from backend.app.services.rag_service import RAGService
from backend.app.utils.response import success_response

router = APIRouter()

@router.post("/sessions", summary="Create a new chat session")
async def create_chat_session(
    payload: ChatSessionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """Initializes a new conversational thread."""
    chat_session = await ChatService.create_session(session, current_user.id, payload.title)
    await session.commit()
    return success_response(
        data=ChatSessionResponse.model_validate(chat_session).model_dump(),
        message="Chat session created successfully"
    )

@router.get("/sessions", summary="List chat sessions")
async def list_chat_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """Returns all active chat sessions for the user."""
    sessions = await ChatService.get_user_sessions(session, current_user.id)
    return success_response(
        data=[ChatSessionResponse.model_validate(s).model_dump() for s in sessions]
    )

@router.get("/sessions/{session_id}/messages", summary="Get chat history")
async def get_chat_history(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """Retrieves all messages for a specific session."""
    chat_session = await ChatService.get_session_by_id(session, current_user.id, session_id)
    messages = await ChatService.get_session_history(session, current_user.id, session_id)
    
    response_data = ChatHistoryResponse(
        session=ChatSessionResponse.model_validate(chat_session),
        messages=[MessageResponse.model_validate(m) for m in messages]
    )
    return success_response(data=response_data.model_dump())

@router.post("/sessions/{session_id}/message", summary="Send a message to the RAG AI")
async def send_message(
    session_id: UUID,
    payload: MessageCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    1. Saves the user's message.
    2. Calls the RAG Engine.
    3. Saves the AI's response.
    4. Returns the AI's response.
    """
    # 1. Verify session exists and belongs to user
    await ChatService.get_session_by_id(session, current_user.id, session_id)
    
    # 2. Save user message to DB
    user_msg = await ChatService.add_message(session, session_id, "user", payload.content)
    await session.commit() # Commit so it's persisted immediately
    
    # 3. Call the RAG Service
    from backend.app.services.document_service import DocumentService
    docs = await DocumentService.get_user_documents(session, current_user.id)
    doc_filenames = [d.filename for d in docs]
    
    # Fetch previous messages for conversation memory (last 10 messages, excluding the one just added)
    all_messages = await ChatService.get_session_history(session, current_user.id, session_id)
    recent_history = all_messages[-11:-1] if len(all_messages) > 1 else []
    formatted_history = [{"role": m.role, "content": m.content} for m in recent_history]

    rag_result = await RAGService.query(
        current_user.id, 
        payload.content, 
        user_documents=doc_filenames,
        chat_history=formatted_history
    )
    
    # 4. Save AI response to DB
    ai_content = rag_result["answer"]
    
    # Build deduplicated source list with real filenames
    if rag_result["sources"]:
        seen_doc_ids = []
        unique_sources = []
        for source in rag_result["sources"]:
            doc_id = source["document_id"]
            if doc_id not in seen_doc_ids:
                seen_doc_ids.append(doc_id)
                unique_sources.append(doc_id)

        if unique_sources:
            ai_content += "\n\n---\n**Sources:**\n"
            for i, doc_id in enumerate(unique_sources):
                # Try to look up the filename from the DB
                try:
                    from sqlalchemy import select as sa_select
                    from backend.app.models.document import Document
                    result = await session.execute(
                        sa_select(Document.filename).where(Document.id == doc_id)
                    )
                    filename = result.scalar_one_or_none() or doc_id
                except Exception:
                    filename = doc_id
                ai_content += f"[{i+1}] 📄 {filename}\n"

    ai_msg = await ChatService.add_message(session, session_id, "assistant", ai_content)
    await session.commit()
    
    # 5. Return the AI message to the user
    return success_response(data=MessageResponse.model_validate(ai_msg).model_dump())

@router.post("/sessions/{session_id}/stream", summary="Stream a message response via SSE")
async def stream_message(
    session_id: UUID,
    payload: MessageCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Streaming version of send_message.
    1. Saves the user message.
    2. Starts streaming the AI response token-by-token via SSE.
    3. Saves the complete response to DB after streaming finishes.
    """
    await ChatService.get_session_by_id(session, current_user.id, session_id)
    await ChatService.add_message(session, session_id, "user", payload.content)
    await session.commit()

    from backend.app.services.document_service import DocumentService
    docs = await DocumentService.get_user_documents(session, current_user.id)
    
    # If user filtered to specific docs, only tell the LLM about those
    if payload.document_ids:
        selected_ids = [str(did) for did in payload.document_ids]
        docs = [d for d in docs if str(d.id) in selected_ids]
    
    doc_filenames = [d.filename for d in docs]

    all_messages = await ChatService.get_session_history(session, current_user.id, session_id)
    recent_history = all_messages[-11:-1] if len(all_messages) > 1 else []
    formatted_history = [{"role": m.role, "content": m.content} for m in recent_history]

    # We need a separate DB session for the background save since we'll close the current one
    # Instead, we collect the full streamed response and save it after yielding all tokens
    collected = [""]

    async def generate():
        import json
        async for chunk in RAGService.stream_query(
            current_user.id,
            payload.content,
            user_documents=doc_filenames,
            chat_history=formatted_history,
            document_ids=payload.document_ids
        ):
            # Parse the SSE chunk to extract text
            if chunk.startswith("data: "):
                data = chunk[6:].strip()
                if data == "[DONE]":
                    # Save complete response to DB using a background session manager
                    try:
                        from backend.app.database.session import DatabaseSessionManager
                        async with DatabaseSessionManager() as background_session:
                            ai_msg = await ChatService.add_message(background_session, session_id, "assistant", collected[0])
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).error(f"Failed to save AI message: {e}")
                    yield chunk
                    return
                elif not data.startswith("[SOURCES]"):
                    # Accumulate the actual text (convert escaped newlines back)
                    collected[0] += data.replace("\\n", "\n")
            yield chunk

    return StreamingResponse(generate(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no"
    })

@router.delete("/sessions/{session_id}", summary="Delete a chat session")
async def delete_chat_session(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """Deletes a specific chat session."""
    await ChatService.delete_session(session, current_user.id, session_id)
    await session.commit()
    return success_response(message="Chat session deleted successfully")
