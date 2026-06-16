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
    def get_document_path(document_id: UUID) -> Path:
        """Returns the local file path for a given document."""
        return Path(settings.UPLOAD_DIR) / str(document_id)

    @staticmethod
    async def save_document(session: AsyncSession, user_id: UUID, file: UploadFile) -> Document:
        """
        Validates file size and extension, creates a DB record, and saves the file to disk.
        """
        # Validate extension
        ext = Path(file.filename).suffix.lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise BadRequestException(f"File extension '{ext}' not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}")
            
        # Create the DB record first to get a UUID
        doc = Document(
            user_id=user_id,
            filename=file.filename,
            file_size=file.size or 0,
            content_type=file.content_type or "application/octet-stream"
        )
        session.add(doc)
        await session.flush()  # Populates doc.id
        
        # Save to disk using the UUID as the filename
        target_path = DocumentService.get_document_path(doc.id)
        
        # Ensure upload dir exists
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file in chunks to avoid memory issues
        try:
            with open(target_path, "wb") as buffer:
                # SpooledTemporaryFile backing the UploadFile can be read sequentially
                while chunk := await file.read(1024 * 1024):  # 1MB chunks
                    buffer.write(chunk)
            
            # Update the exact file size if it wasn't provided by the client
            actual_size = os.path.getsize(target_path)
            
            # Validate size
            if actual_size > settings.MAX_UPLOAD_SIZE:
                os.remove(target_path)
                raise BadRequestException(f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE / (1024*1024)} MB")
                
            doc.file_size = actual_size
            await session.flush()
            
        except Exception as e:
            # Cleanup on failure
            if target_path.exists():
                os.remove(target_path)
            raise BadRequestException(f"Failed to save file: {str(e)}")
            
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
        
        # Delete embeddings from Qdrant so deleted docs no longer appear in chat
        from backend.app.services.vector_db_service import VectorDBService
        VectorDBService.delete_document(doc.id)
