"""
backend/app/api/v1/endpoints/documents.py
=========================================
Endpoints for document upload, listing, and deletion.
"""
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user
from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.schemas.document import DocumentResponse, DocumentListResponse
from backend.app.services.document_service import DocumentService
from backend.app.utils.response import success_response

router = APIRouter()

@router.post("/upload", summary="Upload a new document")
async def upload_document(
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Uploads a file, saves it to disk, and records the metadata.
    """
    doc = await DocumentService.save_document(session, current_user.id, file)
    await session.commit()
    return success_response(
        data=DocumentResponse.model_validate(doc).model_dump(),
        message="Document uploaded successfully"
    )

@router.get("/", response_model=DocumentListResponse, summary="List your documents")
async def list_documents(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Returns all documents uploaded by the authenticated user.
    (Note: Using response_model directly without the success envelope here 
    because we defined DocumentListResponse schema specifically for lists).
    Wait, to keep it consistent, we can return DocumentListResponse directly.
    """
    docs = await DocumentService.get_user_documents(session, current_user.id)
    
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in docs],
        total=len(docs)
    )

@router.get("/{document_id}", summary="Get document metadata")
async def get_document(
    document_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Returns the metadata for a specific document.
    """
    doc = await DocumentService.get_document_by_id(session, current_user.id, document_id)
    return success_response(data=DocumentResponse.model_validate(doc).model_dump())

@router.get("/{document_id}/content", summary="Download/view document content")
async def get_document_content(
    document_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Returns the actual file content for viewing in the browser.
    """
    doc = await DocumentService.get_document_by_id(session, current_user.id, document_id)
    file_path = DocumentService.get_document_path(doc.id)
    
    # If the file doesn't exist on disk, we should handle it gracefully
    if not file_path.exists():
        from backend.app.utils.exceptions import NotFoundException
        raise NotFoundException("Document file missing from disk.")
        
    return FileResponse(
        path=file_path, 
        filename=doc.filename, 
        media_type=doc.content_type,
        content_disposition_type="inline"
    )

@router.post("/{document_id}/process", summary="Parse, chunk, and embed a document")
async def process_document(
    document_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Parses the document text, splits it into chunks, and stores the embeddings in ChromaDB.
    """
    # 1. Verify ownership and get metadata
    doc = await DocumentService.get_document_by_id(session, current_user.id, document_id)
    
    # 2. Get local file path
    file_path = DocumentService.get_document_path(doc.id)
    
    from backend.app.services.parsing_service import ParsingService
    from backend.app.services.chunking_service import ChunkingService
    from backend.app.services.vector_db_service import VectorDBService
    
    # 3. Extract text
    text = ParsingService.extract_text(file_path, doc.content_type)
    
    # 4. Chunk text
    chunks = ChunkingService.chunk_text(text)
    
    # 5. Store in Vector DB
    VectorDBService.add_chunks(doc.id, current_user.id, chunks)
    
    return success_response(
        message=f"Successfully processed {len(chunks)} chunks into the vector database."
    )

@router.delete("/{document_id}", summary="Delete a document")
async def delete_document(
    document_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Deletes the document record and removes the file from disk.
    """
    await DocumentService.delete_document(session, current_user.id, document_id)
    await session.commit()
    return success_response(message="Document deleted successfully")
