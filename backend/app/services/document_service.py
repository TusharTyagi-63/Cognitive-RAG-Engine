"""
backend/app/services/document_service.py
========================================
Business logic for uploading and managing documents.
"""
import os
import shutil
from pathlib import Path
from typing import Sequence
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.models.document import Document
from backend.app.utils.exceptions import NotFoundException, BadRequestException

class DocumentService:
    @staticmethod
    def get_document_path(document_id: UUID, doc: Document = None) -> Path:
        """Returns the local file path for a given document, restoring from DB if missing."""
        path = Path(settings.UPLOAD_DIR) / str(document_id)
        if not path.exists() and doc is not None and getattr(doc, 'file_data', None):
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "wb") as f:
                    f.write(doc.file_data)
            except Exception:
                pass
        return path

    @staticmethod
    async def save_document(session: AsyncSession, user_id: UUID, file: UploadFile) -> Document:
        """
        Validates file size and extension, creates a DB record with cached file bytes,
        and saves the file to disk for local processing.
        """
        # Validate extension
        ext = Path(file.filename).suffix.lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise BadRequestException(f"File extension '{ext}' not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}")
            
        file_bytes = await file.read()
        actual_size = len(file_bytes)
        
        if actual_size > settings.MAX_UPLOAD_SIZE:
            raise BadRequestException(f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE / (1024*1024)} MB")

        # Create the DB record with file_data cached in PostgreSQL
        doc = Document(
            user_id=user_id,
            filename=file.filename,
            file_size=actual_size,
            content_type=file.content_type or "application/octet-stream",
            file_data=file_bytes
        )
        session.add(doc)
        await session.flush()  # Populates doc.id
        
        # Save to disk using the UUID as the filename
        target_path = DocumentService.get_document_path(doc.id)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(target_path, "wb") as buffer:
                buffer.write(file_bytes)
        except Exception as e:
            # If disk write fails on restricted environment, DB still has file_data!
            pass
            
        return doc

    @staticmethod
    async def get_user_documents(session: AsyncSession, user_id: UUID) -> Sequence[Document]:
        """Fetches all documents belonging to a user."""
        result = await session.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.upload_timestamp.desc())
        )
        return result.scalars().all()
        
    @staticmethod
    async def get_document_by_id(session: AsyncSession, user_id: UUID, document_id: UUID) -> Document:
        """Fetches a specific document, ensuring it belongs to the user."""
        result = await session.execute(
            select(Document).where(Document.id == document_id, Document.user_id == user_id)
        )
        doc = result.scalars().first()
        if not doc:
            raise NotFoundException("Document not found or access denied.")
        return doc

    @staticmethod
    async def delete_document(session: AsyncSession, user_id: UUID, document_id: UUID) -> None:
        """Deletes a document from the DB, from disk, and from the vector store."""
        doc = await DocumentService.get_document_by_id(session, user_id, document_id)
        
        # Delete from DB
        await session.delete(doc)
        await session.flush()
        
        # Delete from disk
        target_path = DocumentService.get_document_path(doc.id)
        if target_path.exists():
            os.remove(target_path)
        
        # Delete embeddings from Qdrant in background thread (don't block the response)
        import asyncio
        from backend.app.services.vector_db_service import VectorDBService
        asyncio.get_event_loop().run_in_executor(None, VectorDBService.delete_document, doc.id)
