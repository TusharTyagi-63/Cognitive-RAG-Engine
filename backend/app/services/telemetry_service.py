"""
backend/app/services/telemetry_service.py
=========================================
Telemetry and latency analysis for chat interactions and model performance.
Captures end-to-end metrics:
- Intent classification
- Retrieval time (ms) & matched chunks
- Time to first token (TTFT ms)
- Total LLM generation latency (ms)
- Total end-to-end request latency (ms)
- Prompt size & Context size
- Output tokens/chars & tokens/sec
- Errors & stack traces
"""
from collections import deque
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("chat_telemetry")

class ChatTelemetryService:
    # Keep last 100 interactions in memory for instant API queries
    _recent_events: deque = deque(maxlen=100)
    _log_file: Path = Path("backend/data/chat_telemetry.jsonl")

    @classmethod
    def record_event(cls, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Records a completed or failed chat query event with latency & diagnostic telemetry.
        """
        if "id" not in event:
            event["id"] = str(uuid.uuid4())
        if "timestamp" not in event:
            event["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Append to in-memory deque
        cls._recent_events.appendleft(event)

        # Append to persistent JSONL file
        try:
            cls._log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cls._log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.warning(f"Could not persist chat telemetry to file: {e}")

        # Structured log entry for Render / terminal console inspection
        status = event.get("status", "SUCCESS")
        ttft = event.get("time_to_first_token_ms", 0)
        llm_time = event.get("llm_generation_time_ms", 0)
        total_time = event.get("total_request_time_ms", 0)
        model = event.get("model", "unknown")
        chunks = event.get("chunks_retrieved_count", 0)
        q = (event.get("question", "")[:60] + "...") if len(event.get("question", "")) > 60 else event.get("question", "")
        
        logger.info(
            f"[CHAT TELEMETRY] status={status} | model={model} | TTFT={ttft}ms | "
            f"llm_time={llm_time}ms | total={total_time}ms | chunks={chunks} | query='{q}'"
        )

        return event

    @classmethod
    def get_recent(cls, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns the most recent N chat telemetry events."""
        return list(cls._recent_events)[:limit]

    @classmethod
    def get_summary(cls) -> Dict[str, Any]:
        """Calculates aggregated performance statistics over recent queries."""
        events = list(cls._recent_events)
        if not events:
            return {
                "total_queries": 0,
                "message": "No chat interactions recorded yet in current session."
            }

        successful = [e for e in events if e.get("status") == "SUCCESS"]
        failed = [e for e in events if e.get("status") == "ERROR"]

        ttft_values = [e["time_to_first_token_ms"] for e in successful if e.get("time_to_first_token_ms")]
        llm_time_values = [e["llm_generation_time_ms"] for e in successful if e.get("llm_generation_time_ms")]
        total_time_values = [e["total_request_time_ms"] for e in successful if e.get("total_request_time_ms")]
        retrieval_values = [e["retrieval_time_ms"] for e in successful if e.get("retrieval_time_ms")]

        def avg(nums: List[float]) -> float:
            return round(sum(nums) / len(nums), 2) if nums else 0.0

        return {
            "total_queries": len(events),
            "successful_queries": len(successful),
            "failed_queries": len(failed),
            "error_rate_pct": round((len(failed) / len(events)) * 100, 1) if events else 0,
            "latency_ms": {
                "avg_retrieval_time_ms": avg(retrieval_values),
                "avg_time_to_first_token_ms": avg(ttft_values),
                "avg_model_generation_time_ms": avg(llm_time_values),
                "avg_total_request_time_ms": avg(total_time_values),
                "min_total_ms": min(total_time_values) if total_time_values else 0,
                "max_total_ms": max(total_time_values) if total_time_values else 0,
            },
            "models_used": list(set(e.get("model", "unknown") for e in events)),
            "last_interaction_at": events[0].get("timestamp") if events else None
        }

    @classmethod
    def clear(cls) -> None:
        """Clears in-memory buffer and resets telemetry log file."""
        cls._recent_events.clear()
        try:
            if cls._log_file.exists():
                cls._log_file.unlink()
        except Exception as e:
            logger.warning(f"Could not delete telemetry log file: {e}")
