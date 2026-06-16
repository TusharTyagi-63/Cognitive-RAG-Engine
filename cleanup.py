import asyncio
from backend.app.database.session import DatabaseSessionManager
from sqlalchemy import select
from backend.app.models.document import Document
from backend.app.services.vector_db_service import VectorDBService
from backend.app.core.config import settings
from uuid import UUID

async def main():
    print("Fetching valid document IDs from DB...")
    async with DatabaseSessionManager() as session:
        result = await session.execute(select(Document.id))
        valid_doc_ids = {str(row[0]) for row in result.all()}
    
    print(f"Found {len(valid_doc_ids)} valid documents in DB.")
    
    client = VectorDBService.get_client()
    
    bad_doc_ids = set()
    offset = None
    
    while True:
        records, next_offset = client.scroll(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            limit=1000,
            offset=offset,
            with_payload=["document_id"],
            with_vectors=False
        )
        for record in records:
            doc_id = record.payload.get("document_id")
            if doc_id and doc_id not in valid_doc_ids:
                bad_doc_ids.add(doc_id)
        
        if next_offset is None:
            break
        offset = next_offset

    print("Found orphaned doc IDs:", bad_doc_ids)
    for bad_id in bad_doc_ids:
        print("Deleting chunks for", bad_id)
        VectorDBService.delete_document(UUID(bad_id))

if __name__ == "__main__":
    asyncio.run(main())
