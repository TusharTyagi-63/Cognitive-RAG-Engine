"""
backend/app/services/llm_service.py
===================================
Abstraction layer for calling the LLM API.
Uses the official OpenAI package which acts as a universal adapter
for OpenAI, Groq, TogetherAI, Ollama, vLLM, etc.
"""
from openai import AsyncOpenAI
import logging

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class LLMService:
    _client = None

    @classmethod
    def get_client(cls) -> AsyncOpenAI:
        """Returns a singleton AsyncOpenAI client."""
        if cls._client is None:
            cls._client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL
            )
        return cls._client

    @classmethod
    async def generate_response(cls, system_prompt: str, user_prompt: str, history: list[dict] = None) -> str:
        """
        Calls the LLM with a system prompt, optional history, and user prompt.
        """
        client = cls.get_client()
        
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_prompt})
        
        try:
            response = await client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=4096
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM Generation failed: {str(e)}")
            raise

    @classmethod
    async def stream_response(cls, system_prompt: str, user_prompt: str, history: list[dict] = None):
        """
        Streams LLM response token-by-token using Server-Sent Events.
        Yields raw text chunks as they arrive from the API.
        """
        client = cls.get_client()

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_prompt})

        try:
            stream = await client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=4096,
                stream=True
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            logger.error(f"LLM Streaming failed: {str(e)}")
            raise
