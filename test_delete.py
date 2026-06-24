import asyncio
import uuid
from backend.app.services.vector_db_service import VectorDBService
from qdrant_client.models import Filter, FieldCondition, MatchValue

def test():
    doc_id = uuid.uuid4()
    VectorDBService.delete_document(doc_id)
    print("Success")

if __name__ == "__main__":
    test()
