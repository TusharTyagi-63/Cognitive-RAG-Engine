"""
tests/test_vector_db.py
=======================
Tests for the Qdrant DB integration.
"""
import pytest
from uuid import uuid4

from backend.app.services.vector_db_service import VectorDBService

def test_get_client():
    client = VectorDBService.get_client()
    assert client is not None

def test_add_and_search_chunks():
    doc_id = uuid4()
    user_id = uuid4()
    
    chunks = [
        "The quick brown fox jumps over the lazy dog.",
        "Artificial intelligence is transforming the software industry.",
        "PostgreSQL is an advanced relational database system."
    ]
    
    # Add to DB
    VectorDBService.add_chunks(doc_id, user_id, chunks)
    
    # Search for an AI related query
    results = VectorDBService.search_similar("machine learning and AI", user_id, top_k=1)
    
    assert len(results) == 1
    # The second chunk should be the closest match
    assert "Artificial intelligence" in results[0]["text"]
    assert results[0]["metadata"]["user_id"] == str(user_id)
    assert results[0]["metadata"]["document_id"] == str(doc_id)

def test_tenant_isolation():
    doc_id_1 = uuid4()
    user_id_1 = uuid4()
    
    doc_id_2 = uuid4()
    user_id_2 = uuid4()
    
    chunks1 = ["I love eating apples and bananas."]
    chunks2 = ["My favorite fruits are apples and oranges."]
    
    VectorDBService.add_chunks(doc_id_1, user_id_1, chunks1)
    VectorDBService.add_chunks(doc_id_2, user_id_2, chunks2)
    
    # If user 1 searches for fruits, they should ONLY see their own chunk
    results1 = VectorDBService.search_similar("fruits", user_id_1, top_k=5)
    assert len(results1) == 1
    assert "bananas" in results1[0]["text"]
    
    # If user 2 searches for fruits, they should ONLY see their own chunk
    results2 = VectorDBService.search_similar("fruits", user_id_2, top_k=5)
    assert len(results2) == 1
    assert "oranges" in results2[0]["text"]

def test_delete_document():
    doc_id = uuid4()
    user_id = uuid4()
    
    chunks = ["Temporary data to be deleted."]
    VectorDBService.add_chunks(doc_id, user_id, chunks)
    
    results_before = VectorDBService.search_similar("Temporary data", user_id)
    assert len(results_before) >= 1
    
    # Delete the document
    VectorDBService.delete_document(doc_id)
    
    # Should be empty now for that exact text
    # (Since vector search always returns *something*, we check if the exact text is gone)
    results_after = VectorDBService.search_similar("Temporary data", user_id)
    
    for hit in results_after:
        assert "Temporary data to be deleted." not in hit["text"]
