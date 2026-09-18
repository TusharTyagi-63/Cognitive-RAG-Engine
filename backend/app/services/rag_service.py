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
import asyncio
import time

from backend.app.services.vector_db_service import VectorDBService
from backend.app.services.llm_service import LLMService
from backend.app.services.reranker_service import RerankerService
from backend.app.services.telemetry_service import ChatTelemetryService

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
        4. Returns answer, sources, and latency metrics.
        """
        req_start = time.perf_counter()
        retrieval_start = time.perf_counter()
        retrieval_mode = "dense_vector"

        intent = cls._classify_intent(question)
        logger.info(f"Classified intent as: {intent} for question: '{question}'")

        if intent == "SUMMARY":
            retrieval_mode = "summary_all"
            results = await asyncio.to_thread(VectorDBService.get_all_chunks, user_id, 40, document_ids)
            system_msg = cls.SUMMARY_SYSTEM_PROMPT
        else:
            results = await asyncio.to_thread(VectorDBService.search_similar, question, user_id, 5, document_ids)
            system_msg = cls.SYSTEM_PROMPT

        # Format Context
        if not results:
            context_block = "No document content found."
            sources = []
            # Fallback: if vector search returned 0 chunks but user has documents on disk
            if user_documents:
                try:
                    from backend.app.services.document_service import DocumentService
                    from backend.app.services.parsing_service import ParsingService
                    from backend.app.database.connection import async_session_factory
                    async with async_session_factory() as db_session:
                        user_docs = await DocumentService.get_user_documents(db_session, user_id)
                        fallback_pieces = []
                        for d in user_docs[:4]:
                            fpath = DocumentService.get_document_path(d.id)
                            if fpath.exists():
                                txt = await asyncio.to_thread(ParsingService.extract_text, fpath, d.content_type)
                                if txt:
                                    snippet = txt[:3500]
                                    fallback_pieces.append(f"--- DOCUMENT: {d.filename} ---\n{snippet}\n")
                                    sources.append({
                                        "document_id": str(d.id),
                                        "chunk_index": 0,
                                        "content": snippet[:1000],
                                        "score": 0.92
                                    })
                        if fallback_pieces:
                            context_block = "\n".join(fallback_pieces)
                            results = True
                            retrieval_mode = "fallback_disk"
                except Exception as e:
                    logger.error(f"Fallback extraction failed: {e}")
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
                    "content": text,
                    "text_snippet": text[:100] + "...",
                    "score": hit.get("score", 0.95),
                })
            context_block = "\n".join(context_pieces)

        retrieval_time_ms = round((time.perf_counter() - retrieval_start) * 1000, 2)

        # Append document list to system prompt
        if user_documents:
            system_msg += f"\n\nSystem Info: The user has uploaded {len(user_documents)} document(s): {', '.join(user_documents)}."

        user_prompt = f"Document Context:\n{context_block}\n\nUser Question:\n{question}"

        # Generate Answer
        model_name = LLMService.get_model()
        llm_start = time.perf_counter()

        if not results and not chat_history:
            answer = "I do not have any documents to search through. Please upload some documents first."
            llm_time_ms = 0.0
        else:
            try:
                answer = await LLMService.generate_response(system_msg, user_prompt, history=chat_history)
                llm_time_ms = round((time.perf_counter() - llm_start) * 1000, 2)
            except Exception as e:
                total_time_ms = round((time.perf_counter() - req_start) * 1000, 2)
                import traceback
                ChatTelemetryService.record_event({
                    "user_id": str(user_id),
                    "question": question,
                    "intent": intent,
                    "retrieval_mode": retrieval_mode,
                    "retrieval_time_ms": retrieval_time_ms,
                    "chunks_retrieved_count": len(sources),
                    "model": model_name,
                    "total_request_time_ms": total_time_ms,
                    "status": "ERROR",
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
                raise

        total_time_ms = round((time.perf_counter() - req_start) * 1000, 2)

        metrics = {
            "retrieval_time_ms": retrieval_time_ms,
            "llm_generation_time_ms": llm_time_ms,
            "total_request_time_ms": total_time_ms,
            "model": model_name,
            "chunks_count": len(sources)
        }

        ChatTelemetryService.record_event({
            "user_id": str(user_id),
            "question": question,
            "intent": intent,
            "retrieval_mode": retrieval_mode,
            "retrieval_time_ms": retrieval_time_ms,
            "chunks_retrieved_count": len(sources),
            "chunks_summary": [
                {
                    "doc_id": s.get("document_id"),
                    "score": s.get("score"),
                    "preview": s.get("content", s.get("text_snippet", ""))[:120]
                } for s in sources[:5]
            ],
            "context_chars": len(context_block),
            "model": model_name,
            "time_to_first_token_ms": None,
            "llm_generation_time_ms": llm_time_ms,
            "total_request_time_ms": total_time_ms,
            "response_chars": len(answer),
            "status": "SUCCESS"
        })

        return {
            "answer": answer,
            "sources": sources,
            "metrics": metrics
        }

    @classmethod
    async def stream_query(cls, user_id: UUID, question: str, top_k: int = 5, user_documents: List[str] = None, chat_history: List[Dict[str, str]] = None, document_ids: List[UUID] = None):
        """
        Streaming version of query().
        Retrieves context then streams LLM response token-by-token.
        Yields tokens, [METRICS], [SOURCES], and [DONE].
        """
        import json
        req_start = time.perf_counter()
        retrieval_start = time.perf_counter()
        retrieval_mode = "dense_vector"

        intent = cls._classify_intent(question)

        if intent == "SUMMARY":
            retrieval_mode = "summary_all"
            results = await asyncio.to_thread(VectorDBService.get_all_chunks, user_id, 40, document_ids)
            system_msg = cls.SUMMARY_SYSTEM_PROMPT
        else:
            results = await asyncio.to_thread(VectorDBService.search_similar, question, user_id, 5, document_ids)
            system_msg = cls.SYSTEM_PROMPT

        if not results:
            context_block = "No document content found."
            sources = []
            # Resilient fallback: parse documents directly from disk if vector search was empty
            if user_documents:
                try:
                    from backend.app.services.document_service import DocumentService
                    from backend.app.services.parsing_service import ParsingService
                    from backend.app.database.connection import async_session_factory
                    async with async_session_factory() as db_session:
                        user_docs = await DocumentService.get_user_documents(db_session, user_id)
                        fallback_pieces = []
                        for d in user_docs[:4]:
                            fpath = DocumentService.get_document_path(d.id)
                            if fpath.exists():
                                txt = await asyncio.to_thread(ParsingService.extract_text, fpath, d.content_type)
                                if txt:
                                    snippet = txt[:3500]
                                    fallback_pieces.append(f"--- DOCUMENT: {d.filename} ---\n{snippet}\n")
                                    sources.append({
                                        "document_id": str(d.id),
                                        "chunk_index": 0,
                                        "content": snippet[:1000],
                                        "score": 0.92
                                    })
                        if fallback_pieces:
                            context_block = "\n".join(fallback_pieces)
                            results = True
                            retrieval_mode = "fallback_disk"
                except Exception as e:
                    logger.error(f"Fallback stream extraction failed: {e}")
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
                    "content": text,
                    "score": hit.get("score", 0.95),
                })
            context_block = "\n".join(context_pieces)

        retrieval_time_ms = round((time.perf_counter() - retrieval_start) * 1000, 2)

        if user_documents:
            system_msg += f"\n\nSystem Info: The user has uploaded {len(user_documents)} document(s): {', '.join(user_documents)}."

        user_prompt = f"Document Context:\n{context_block}\n\nUser Question:\n{question}"
        model_name = LLMService.get_model()

        if not results and not chat_history:
            total_req_time_ms = round((time.perf_counter() - req_start) * 1000, 2)
            ChatTelemetryService.record_event({
                "user_id": str(user_id),
                "question": question,
                "intent": intent,
                "retrieval_mode": retrieval_mode,
                "retrieval_time_ms": retrieval_time_ms,
                "chunks_retrieved_count": 0,
                "model": model_name,
                "time_to_first_token_ms": 0,
                "llm_generation_time_ms": 0,
                "total_request_time_ms": total_req_time_ms,
                "response_chars": 0,
                "status": "SUCCESS",
                "notes": "No documents available"
            })
            yield "data: I do not have any documents to search through. Please upload some documents first.\n\n"
            yield "data: [DONE]\n\n"
            return

        llm_start = time.perf_counter()
        first_token_time = None
        full_response = ""

        try:
            async for token in LLMService.stream_response(system_msg, user_prompt, history=chat_history):
                if first_token_time is None:
                    first_token_time = time.perf_counter()
                full_response += token
                # Escape newlines for SSE format
                safe_token = token.replace("\n", "\\n")
                yield f"data: {safe_token}\n\n"

            llm_end = time.perf_counter()
            ttft_ms = round(((first_token_time or llm_end) - llm_start) * 1000, 2)
            llm_gen_ms = round((llm_end - llm_start) * 1000, 2)
            total_time_ms = round((llm_end - req_start) * 1000, 2)

            telemetry_payload = {
                "user_id": str(user_id),
                "question": question,
                "intent": intent,
                "retrieval_mode": retrieval_mode,
                "retrieval_time_ms": retrieval_time_ms,
                "chunks_retrieved_count": len(sources),
                "chunks_summary": [
                    {
                        "doc_id": s.get("document_id"),
                        "score": s.get("score"),
                        "preview": s.get("content", "")[:120]
                    } for s in sources[:5]
                ],
                "context_chars": len(context_block),
                "model": model_name,
                "time_to_first_token_ms": ttft_ms,
                "llm_generation_time_ms": llm_gen_ms,
                "total_request_time_ms": total_time_ms,
                "response_chars": len(full_response),
                "status": "SUCCESS"
            }
            ChatTelemetryService.record_event(telemetry_payload)

            # Yield metrics event before [SOURCES] and [DONE]
            metrics_event = {
                "ttft_ms": ttft_ms,
                "llm_time_ms": llm_gen_ms,
                "total_time_ms": total_time_ms,
                "retrieval_time_ms": retrieval_time_ms,
                "model": model_name,
                "chunks_count": len(sources)
            }
            yield f"data: [METRICS]{json.dumps(metrics_event)}\n\n"
            yield f"data: [SOURCES]{json.dumps(sources)}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            err_time_ms = round((time.perf_counter() - req_start) * 1000, 2)
            import traceback
            ChatTelemetryService.record_event({
                "user_id": str(user_id),
                "question": question,
                "intent": intent,
                "retrieval_mode": retrieval_mode,
                "retrieval_time_ms": retrieval_time_ms,
                "chunks_retrieved_count": len(sources),
                "model": model_name,
                "total_request_time_ms": err_time_ms,
                "status": "ERROR",
                "error": str(e),
                "traceback": traceback.format_exc()
            })
            raise
