from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

try:
    client = QdrantClient(host="localhost", port=6333)
    print("Connected to Qdrant")
    
    for doc_id in ["1b6b337e-74ff-492d-82b5-c17c88e0d1d6", "bfe9545c-079b-499a-a1c8-4e8fcaa9668e"]:
        print(f"Deleting orphaned chunks for document {doc_id}")
        client.delete(
            collection_name="rag_documents",
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=doc_id)
                    )
                ]
            )
        )
    print("Done cleaning Qdrant.")
except Exception as e:
    print(f"Error: {e}")
