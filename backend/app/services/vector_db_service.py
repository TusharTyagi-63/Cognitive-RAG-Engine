"""
backend/app/services/vector_db_service.py
=========================================
Service layer for interacting with Qdrant for storing and searching vector embeddings.
"""
from typing import List, Dict, Any
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, MatchAny
from fastembed import TextEmbedding

from backend.app.core.config import settings

class VectorDBService:
    _client = None
    _model = None

    @classmethod
    def get_model(cls) -> TextEmbedding:
        """Returns the embedding model, loading it into RAM only when needed."""
        if cls._model is None:
            cls._model = TextEmbedding("BAAI/bge-small-en-v1.5", threads=1)
        return cls._model

    @classmethod
    def unload_model(cls) -> None:
        """Frees the embedding model from RAM to prevent OOM crashes on Render."""
        if cls._model is not None:
            cls._model = None
            import gc
            gc.collect()

    @classmethod
    def get_client(cls) -> QdrantClient:
        """Returns a singleton QdrantClient connected to the local persist directory."""
        if cls._client is None:
            if settings.QDRANT_API_KEY:
                cls._client = QdrantClient(url=settings.QDRANT_HOST, api_key=settings.QDRANT_API_KEY)
            elif settings.QDRANT_HOST in ["localhost", "127.0.0.1"] and settings.is_production:
                # Render free tier: fallback to local disk storage
                cls._client = QdrantClient(path="./qdrant_data")
            else:
                try:
                    cls._client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
                except Exception:
                    # Fallback to local path if connection refused
                    cls._client = QdrantClient(path="./qdrant_data")
            
            # Ensure collection exists
            collections = cls._client.get_collections().collections
            from qdrant_client.models import PayloadSchemaType
            if not any(c.name == settings.QDRANT_COLLECTION_NAME for c in collections):
                cls._client.create_collection(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=384, 
                        distance=Distance.COSINE,
                        on_disk=True  # Force vectors to disk to save RAM
                    ),
                    on_disk_payload=True  # Force payload to disk to save RAM
                )
            
            # Ensure indices exist so delete operations don't fail
            try:
                cls._client.create_payload_index(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    field_name="document_id",
                    field_schema=PayloadSchemaType.KEYWORD,
                )
                cls._client.create_payload_index(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    field_name="user_id",
                    field_schema=PayloadSchemaType.KEYWORD,
                )
            except Exception as e:
                logger.warning(f"Could not create payload index (might already exist): {e}")
                
        return cls._client

    @classmethod
    async def add_chunks_async(cls, document_id: UUID, user_id: UUID, chunks: List[str]) -> None:
        """
        Embeds and stores text chunks in Qdrant.
        Runs in small batches and yields to the event loop to prevent CPU starvation.
        """
        if not chunks:
            return

        client = cls.get_client()
        import asyncio
        import uuid
        
        # Process in tiny batches of 4 to minimize intermediate tensor memory
        batch_size = 4
        for i in range(0, len(chunks), batch_size):
            chunk_batch = chunks[i:i+batch_size]
            
            # 1. Embed this small batch in a thread
            def embed_batch():
                model = cls.get_model()
                return list(model.embed(chunk_batch, batch_size=batch_size))
                
            embeddings = await asyncio.to_thread(embed_batch)
            
            import gc
            gc.collect()

            # 2. Prepare points
            points = []
            for j, (chunk, embedding) in enumerate(zip(chunk_batch, embeddings)):
                points.append(PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding.tolist() if hasattr(embedding, "tolist") else embedding,
                    payload={
                        "document_id": str(document_id),
                        "user_id": str(user_id),
                        "chunk_index": i + j,
                        "text": chunk
                    }
                ))
            
            # 3. Upsert points in a thread
            def upsert_batch():
                client.upsert(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    points=points
                )
            await asyncio.to_thread(upsert_batch)
            
            # 4. Yield to the event loop so health checks can pass!
            await asyncio.sleep(0.1)
            
        # Free the model from RAM after processing the document
        cls.unload_model()

    @classmethod
    def search_similar(cls, query: str, user_id: UUID, top_k: int = 5, document_ids: List[UUID] = None) -> List[Dict[str, Any]]:
        """
        Searches the vector database for chunks similar to the query.
        Critically, restricts the search space to chunks owned by the specified user_id.
        If document_ids is provided, further restricts to only those documents.
        """
        client = cls.get_client()
        model = cls.get_model()
        
        query_vector = list(model.embed([query]))[0]
        
        must_conditions = [
            FieldCondition(key="user_id", match=MatchValue(value=str(user_id)))
        ]
        if document_ids:
            must_conditions.append(
                FieldCondition(key="document_id", match=MatchAny(any=[str(did) for did in document_ids]))
            )
            
        search_result = client.search(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            query_vector=query_vector.tolist(),
            query_filter=Filter(must=must_conditions),
            limit=top_k
        )
        
        formatted_results = []
        for hit in search_result:
            formatted_results.append({
                "text": hit.payload.get("text", ""),
                "metadata": {
                    "document_id": hit.payload.get("document_id"),
                    "user_id": hit.payload.get("user_id"),
                    "chunk_index": hit.payload.get("chunk_index")
                },
                "score": hit.score
            })
            
        # Free model from RAM
        cls.unload_model()
            
        return formatted_results

    @classmethod
    def hybrid_search(cls, query: str, user_id: UUID, top_k: int = 10, document_ids: List[UUID] = None) -> List[Dict[str, Any]]:
        """
        Hybrid search combining dense vector search (semantic) with BM25 (keyword).
        """
        from rank_bm25 import BM25Okapi

        # 1. Dense vector search — retrieve more candidates for fusion
        dense_results = cls.search_similar(query, user_id, top_k=top_k, document_ids=document_ids)

        if not dense_results:
            return []

        # 2. Fetch all available chunks for BM25 (we only BM25-search what we already have)
        all_chunks = cls.get_all_chunks(user_id, limit=200, document_ids=document_ids)

        if not all_chunks:
            return dense_results

        # 3. Build BM25 index over all user chunks
        tokenized_corpus = [chunk["text"].lower().split() for chunk in all_chunks]
        bm25 = BM25Okapi(tokenized_corpus)

        # 4. BM25 search
        tokenized_query = query.lower().split()
        bm25_scores = bm25.get_scores(tokenized_query)

        # Sort by score, get top_k indices
        import numpy as np
        bm25_top_indices = np.argsort(bm25_scores)[::-1][:top_k]
        bm25_results = [all_chunks[i] for i in bm25_top_indices if bm25_scores[i] > 0]

        # 5. Reciprocal Rank Fusion (RRF)
        k = 60  # RRF constant
        rrf_scores: Dict[str, float] = {}
        chunk_map: Dict[str, Dict] = {}

        # Index dense results
        for rank, result in enumerate(dense_results):
            uid = f"{result['metadata']['document_id']}_{result['metadata']['chunk_index']}"
            rrf_scores[uid] = rrf_scores.get(uid, 0) + 1 / (k + rank + 1)
            chunk_map[uid] = result

        # Index BM25 results
        for rank, result in enumerate(bm25_results):
            uid = f"{result['metadata']['document_id']}_{result['metadata']['chunk_index']}"
            rrf_scores[uid] = rrf_scores.get(uid, 0) + 1 / (k + rank + 1)
            if uid not in chunk_map:
                chunk_map[uid] = result

        # 6. Sort by combined RRF score
        sorted_uids = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)
        fused_results = []
        for uid in sorted_uids[:top_k]:
            result = chunk_map[uid]
            result["score"] = rrf_scores[uid]
            fused_results.append(result)

        logger.info(f"Hybrid search: {len(dense_results)} dense + {len(bm25_results)} BM25 → {len(fused_results)} fused results")
        return fused_results

    @classmethod
    def get_all_chunks(cls, user_id: UUID, limit: int = 30, document_ids: List[UUID] = None) -> List[Dict[str, Any]]:
        """
        Retrieves all chunks for a user's documents in chunk_index order.
        Used for full-document summarization, bypassing vector search.
        """
        client = cls.get_client()
        
        must_conditions = [
            FieldCondition(key="user_id", match=MatchValue(value=str(user_id)))
        ]
        if document_ids:
            must_conditions.append(
                FieldCondition(key="document_id", match=MatchAny(any=[str(did) for did in document_ids]))
            )
            
        results, _ = client.scroll(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            scroll_filter=Filter(must=must_conditions),
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        
        # Sort by document_id and then chunk_index for coherent reading order
        sorted_results = sorted(
            results,
            key=lambda p: (p.payload.get("document_id", ""), p.payload.get("chunk_index", 0))
        )
        
        return [
            {
                "text": p.payload.get("text", ""),
                "metadata": {
                    "document_id": p.payload.get("document_id"),
                    "user_id": p.payload.get("user_id"),
                    "chunk_index": p.payload.get("chunk_index")
                },
                "score": 1.0
            }
            for p in sorted_results
        ]

    @classmethod
    def delete_document(cls, document_id: UUID) -> None:
        """Deletes all chunks associated with a specific document."""
        client = cls.get_client()
        client.delete(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=str(document_id))
                    )
                ]
            )
        )
