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
    Uploads a file, saves bytes to PostgreSQL, saves to disk, and records the metadata.
    Attempts immediate text extraction so extracted_text is ready immediately.
    """
    import asyncio
    doc = await DocumentService.save_document(session, current_user.id, file)

    try:
        from backend.app.services.parsing_service import ParsingService
        file_path = DocumentService.get_document_path(doc.id, doc=doc)
        txt = await asyncio.to_thread(ParsingService.extract_text, file_path, doc.content_type, doc.filename)
        if txt and txt.strip():
            doc.extracted_text = txt
    except Exception as e:
        import logging
        logging.getLogger(__name__).debug(f"Immediate parse skipped for background processing: {e}")

    await session.commit()
    return success_response(
        data=DocumentResponse.model_validate(doc).model_dump(),
        message="Document uploaded successfully"
    )

@router.get("", response_model=DocumentListResponse, include_in_schema=False)
@router.get("/", response_model=DocumentListResponse, summary="List your documents")
async def list_documents(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Returns all documents uploaded by the authenticated user.
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
    Restores transparently from PostgreSQL if the cloud container restarted.
    """
    from fastapi import Response
    doc = await DocumentService.get_document_by_id(session, current_user.id, document_id)
    file_path = DocumentService.get_document_path(doc.id, doc=doc)
    
    if file_path.exists():
        return FileResponse(
            path=file_path, 
            filename=doc.filename, 
            media_type=doc.content_type,
            content_disposition_type="inline"
        )
    elif getattr(doc, 'file_data', None):
        return Response(
            content=doc.file_data,
            media_type=doc.content_type,
            headers={"Content-Disposition": f'inline; filename="{doc.filename}"'}
        )
    else:
        from backend.app.utils.exceptions import NotFoundException
        raise NotFoundException("Document file missing from cloud storage. Please re-upload.")

from fastapi import BackgroundTasks

async def _process_in_background(document_id: UUID, user_id: UUID):
    from backend.app.services.document_service import DocumentService
    from backend.app.services.parsing_service import ParsingService
    from backend.app.services.chunking_service import ChunkingService
    from backend.app.services.vector_db_service import VectorDBService
    import asyncio
    
    from backend.app.database.connection import async_session_factory
    async with async_session_factory() as session:
        doc = await DocumentService.get_document_by_id(session, user_id, document_id)
        file_path = DocumentService.get_document_path(doc.id, doc=doc)
        
        try:
            text = await asyncio.to_thread(ParsingService.extract_text, file_path, doc.content_type, doc.filename)
            if text and text.strip():
                # Persist extracted text directly in PostgreSQL for cloud durability
                doc.extracted_text = text
                await session.commit()
                
            chunks = await asyncio.to_thread(ChunkingService.chunk_text, text)
            if chunks:
                await VectorDBService.add_chunks_async(doc.id, user_id, chunks, filename=doc.filename)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Background processing failed for document {document_id}: {e}")

@router.post("/{document_id}/process", summary="Parse, chunk, and embed a document")
async def process_document(
    document_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    background_tasks: BackgroundTasks
):
    """
    Parses the document text, splits it into chunks, and stores the embeddings in ChromaDB.
    Runs in the background to prevent timeouts on large documents.
    """
    # 1. Verify ownership
    await DocumentService.get_document_by_id(session, current_user.id, document_id)
    
    # 2. Add to background tasks
    background_tasks.add_task(_process_in_background, document_id, current_user.id)
    
    return success_response(
        message="Document processing started in the background."
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
