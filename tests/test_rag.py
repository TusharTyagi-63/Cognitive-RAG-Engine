"""
tests/test_rag.py
=================
Tests for the Retrieval-Augmented Generation orchestrator.
"""
import pytest
from unittest.mock import patch, AsyncMock
from uuid import uuid4

from backend.app.services.rag_service import RAGService
from backend.app.services.vector_db_service import VectorDBService

@pytest.fixture
def mock_vector_db():
    with patch.object(VectorDBService, 'search_similar') as mock:
        yield mock

@pytest.fixture
def mock_llm_service():
    with patch('backend.app.services.rag_service.LLMService.generate_response', new_callable=AsyncMock) as mock:
        yield mock

@pytest.mark.asyncio
async def test_rag_query_no_documents(mock_vector_db, mock_llm_service):
    # Setup mock to return empty list
    mock_vector_db.return_value = []
    
    user_id = uuid4()
    result = await RAGService.query(user_id, "What is AI?")
    
    # Should short-circuit and not call the LLM
    assert "Please upload some documents first" in result["answer"]
    assert len(result["sources"]) == 0
    assert mock_llm_service.call_count == 0

@pytest.mark.asyncio
async def test_rag_query_with_documents(mock_vector_db, mock_llm_service):
    # Setup mock vector search results
    doc_id = str(uuid4())
    mock_vector_db.return_value = [
        {
            "text": "Artificial Intelligence (AI) is the simulation of human intelligence.",
            "metadata": {"document_id": doc_id, "chunk_index": 0}
        }
    ]
    
    # Setup mock LLM response
    mock_llm_service.return_value = "AI is the simulation of human intelligence."
    
    user_id = uuid4()
    result = await RAGService.query(user_id, "What is AI?")
    
    # Verify vector DB was called with correct arguments
    mock_vector_db.assert_called_once_with("What is AI?", user_id, 5)
    
    # Verify LLM was called with the assembled prompt
    mock_llm_service.assert_called_once()
    system_prompt, user_prompt = mock_llm_service.call_args[0]
    
    assert "Expert AI assistant" in system_prompt or "expert AI assistant" in system_prompt
    assert "Artificial Intelligence (AI) is the simulation of human intelligence." in user_prompt
    assert "What is AI?" in user_prompt
    
    # Verify final result
    assert result["answer"] == "AI is the simulation of human intelligence."
    assert len(result["sources"]) == 1
    assert result["sources"][0]["document_id"] == doc_id
