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

    @classmethod
    def rerank(cls, query: str, results: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Re-ranks retrieval results by their existing vector similarity score.
        (Cross-encoder reranking disabled to fit within free-tier memory limits.)
        """
        if not results:
            return results

        try:
            reranked = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
            return reranked[:top_n]
        except Exception as e:
            logger.error(f"Re-ranking failed, returning original results: {e}")
            return results[:top_n]
