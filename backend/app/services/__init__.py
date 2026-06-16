"""
backend/app/services/__init__.py
==================================
Services layer — business logic for the Cognitive RAG Engine.

This package will contain the core domain services:

Phase 2 — Authentication
-------------------------
- UserService   : User registration, login, token refresh, profile management.

Phase 3 — Document Management
------------------------------
- DocumentService : Upload, parse, chunk, and store documents.
- ChunkService    : Manage document chunks and metadata.

Phase 4 — RAG Pipeline
-----------------------
- EmbeddingService : Generate embeddings via OpenAI / local models.
- VectorStoreService : Interact with ChromaDB for similarity search.
- RetrievalService : Orchestrate document retrieval given a user query.
- GenerationService : Feed retrieved context to an LLM and return answers.

Design Principles
-----------------
- Each service class receives its dependencies (database session, external
  client, config) via constructor injection — not module-level globals.
- Services are stateless: they hold no request-scoped state, only shared
  resources like a database session passed per-call.
- FastAPI endpoints obtain service instances via `Depends()` factories defined
  alongside each service class.
"""
