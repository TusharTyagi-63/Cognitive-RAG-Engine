"""
backend/app/services/reranker_service.py
=========================================
Cross-encoder re-ranker for improving retrieval precision.

After vector/hybrid search retrieves the top-K candidates, the cross-encoder
re-scores every (query, chunk) pair jointly — unlike bi-encoders which embed
them separately. This produces significantly more accurate relevance scores,
especially for long or ambiguous queries.

Model: cross-encoder/ms-marco-MiniLM-L-6-v2
  - Trained on MS MARCO passage ranking dataset (501k queries)
  - Very fast (MiniLM architecture)
  - State-of-the-art for passage re-ranking tasks
"""
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class RerankerService:
    _model = None

    @classmethod
    def get_model(cls):
        """Returns the singleton cross-encoder model (lazy-loaded)."""
        if cls._model is None:
            from sentence_transformers import CrossEncoder
            logger.info("Loading cross-encoder re-ranker model...")
            cls._model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512)
            logger.info("Re-ranker model loaded.")
        return cls._model

    @classmethod
    def rerank(cls, query: str, results: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Re-ranks retrieval results using a cross-encoder model.

        Args:
            query:   The user's search query.
            results: List of retrieval results from hybrid/vector search.
            top_n:   Number of top results to return after re-ranking.

        Returns:
            A filtered, re-ranked list of results sorted by cross-encoder score.
        """
        if not results:
            return results

        try:
            model = cls.get_model()
            pairs = [(query, r["text"]) for r in results]
            scores = model.predict(pairs)

            # Attach scores and sort
            for i, result in enumerate(results):
                result["rerank_score"] = float(scores[i])

            reranked = sorted(results, key=lambda x: x["rerank_score"], reverse=True)
            return reranked[:top_n]
        except Exception as e:
            logger.error(f"Re-ranking failed, returning original results: {e}")
            return results[:top_n]
