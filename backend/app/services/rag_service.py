"""
backend/app/services/rag_service.py
===================================
Orchestrates the Retrieval-Augmented Generation (RAG) pipeline.
Includes an Intent Router that dynamically selects the retrieval strategy:
  - SEARCH: Standard vector similarity search for specific questions.
  - SUMMARY: Full sequential chunk retrieval for global summarization tasks.
"""
from typing import Dict, Any, List
from uuid import UUID

from backend.app.services.vector_db_service import VectorDBService
from backend.app.services.llm_service import LLMService
from backend.app.services.reranker_service import RerankerService

import logging
logger = logging.getLogger(__name__)

SUMMARY_INTENTS = [
    "summarize", "summarise", "summary", "overview", "explain",
    "describe", "what is this", "what does this", "tell me about",
    "give me an idea", "brief", "outline", "tldr", "tl;dr",
    "main points", "key points", "what is the paper", "what is the document",
    "what is this about", "explain this", "explain the"
]

class RAGService:
    SYSTEM_PROMPT = """You are a highly intelligent, expert research assistant.
Your task is to answer the user's questions based primarily on the context extracted from their uploaded documents, while also keeping in mind the ongoing conversation history.
If the context does not contain the answer, and the answer is not established in the conversation history, simply say "I do not have enough information in the provided documents to answer that."
Do not hallucinate. Cite your sources when using information from the context.
Format your responses using clean, readable Markdown."""

    SUMMARY_SYSTEM_PROMPT = """You are an expert research analyst and technical writer.
You have been provided with the full, sequential content of a document.
Your task is to generate a comprehensive, well-structured, and insightful summary.
Organize your summary with clear headings, bullet points for key details, and a conclusion section.
Format your response using clean, readable Markdown."""

    @classmethod
    def _classify_intent(cls, question: str) -> str:
        """
        Classifies whether the user wants a full-document summary or a specific search.
        Uses simple keyword heuristics for speed — no extra LLM call needed.
        Returns 'SUMMARY' or 'SEARCH'.
        """
        q_lower = question.lower().strip()
        for keyword in SUMMARY_INTENTS:
            if keyword in q_lower:
                return "SUMMARY"
        return "SEARCH"

    @classmethod
    async def query(cls, user_id: UUID, question: str, top_k: int = 5, user_documents: List[str] = None, chat_history: List[Dict[str, str]] = None, document_ids: List[UUID] = None) -> Dict[str, Any]:
        """
        1. Classifies intent (SUMMARY vs SEARCH).
        2. Retrieves context using the appropriate strategy.
        3. Calls LLM with full context + conversation history.
        4. Returns answer and sources.
        """
        intent = cls._classify_intent(question)
        logger.info(f"Classified intent as: {intent} for question: '{question}'")

        if intent == "SUMMARY":
            # Full document retrieval path
            results = VectorDBService.get_all_chunks(user_id, limit=40, document_ids=document_ids)
            system_msg = cls.SUMMARY_SYSTEM_PROMPT
        else:
            # Replaced heavy BM25 hybrid search and cross-encoder re-ranking with fast dense search
            results = VectorDBService.search_similar(question, user_id, top_k=5, document_ids=document_ids)
            system_msg = cls.SYSTEM_PROMPT

        # Format Context
        if not results:
            context_block = "No document content found."
            sources = []
        else:
            context_pieces = []
            sources = []
            for i, hit in enumerate(results):
                text = hit["text"]
                metadata = hit["metadata"]
                context_pieces.append(f"--- CHUNK {i+1} ---\n{text}\n")
                sources.append({
                    "document_id": metadata.get("document_id"),
                    "chunk_index": metadata.get("chunk_index"),
                    "text_snippet": text[:100] + "..."
                })
            context_block = "\n".join(context_pieces)

        # Append document list to system prompt
        if user_documents:
            system_msg += f"\n\nSystem Info: The user has uploaded {len(user_documents)} document(s): {', '.join(user_documents)}."

        user_prompt = f"Document Context:\n{context_block}\n\nUser Question:\n{question}"

        # Generate Answer
        if not results and not chat_history:
            answer = "I do not have any documents to search through. Please upload some documents first."
        else:
            answer = await LLMService.generate_response(system_msg, user_prompt, history=chat_history)

        return {
            "answer": answer,
            "sources": sources
        }

    @classmethod
    async def stream_query(cls, user_id: UUID, question: str, top_k: int = 5, user_documents: List[str] = None, chat_history: List[Dict[str, str]] = None, document_ids: List[UUID] = None):
        """
        Streaming version of query().
        Retrieves context then streams LLM response token-by-token.
        Also yields a final [SOURCES] event with source metadata.
        """
        import json
        intent = cls._classify_intent(question)

        if intent == "SUMMARY":
            results = VectorDBService.get_all_chunks(user_id, limit=40, document_ids=document_ids)
            system_msg = cls.SUMMARY_SYSTEM_PROMPT
        else:
            # Replaced heavy BM25 hybrid search and cross-encoder re-ranking with fast dense search
            results = VectorDBService.search_similar(question, user_id, top_k=5, document_ids=document_ids)
            system_msg = cls.SYSTEM_PROMPT

        if not results:
            context_block = "No document content found."
            sources = []
        else:
            context_pieces = []
            sources = []
            for i, hit in enumerate(results):
                text = hit["text"]
                metadata = hit["metadata"]
                context_pieces.append(f"--- CHUNK {i+1} ---\n{text}\n")
                sources.append({
                    "document_id": metadata.get("document_id"),
                    "chunk_index": metadata.get("chunk_index"),
                })
            context_block = "\n".join(context_pieces)

        if user_documents:
            system_msg += f"\n\nSystem Info: The user has uploaded {len(user_documents)} document(s): {', '.join(user_documents)}."

        user_prompt = f"Document Context:\n{context_block}\n\nUser Question:\n{question}"

        if not results and not chat_history:
            yield "data: I do not have any documents to search through. Please upload some documents first.\n\n"
            yield "data: [DONE]\n\n"
            return

        full_response = ""
        async for token in LLMService.stream_response(system_msg, user_prompt, history=chat_history):
            full_response += token
            # Escape newlines for SSE format
            safe_token = token.replace("\n", "\\n")
            yield f"data: {safe_token}\n\n"

        # Send sources as a final event
        yield f"data: [SOURCES]{json.dumps(sources)}\n\n"
        yield "data: [DONE]\n\n"
