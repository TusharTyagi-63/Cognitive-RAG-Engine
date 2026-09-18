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
        """
        Returns a singleton AsyncOpenAI client.
        Automatically uses Gemini OpenAI-compatible endpoint when GEMINI_API_KEY is available
        and OPENAI_API_KEY is unset or dummy.
        """
        if cls._client is None:
            # Check if we should fallback to Google Gemini's official OpenAI-compatible endpoint
            use_gemini = (
                bool(settings.GEMINI_API_KEY)
                and (not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "dummy_key_for_now")
            )
            if use_gemini:
                logger.info("Initializing LLMService with Google Gemini OpenAI-compatible endpoint.")
                cls._client = AsyncOpenAI(
                    api_key=settings.GEMINI_API_KEY,
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
                )
            else:
                logger.info(f"Initializing LLMService with base_url={settings.OPENAI_BASE_URL}")
                cls._client = AsyncOpenAI(
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL
                )
        return cls._client

    @classmethod
    def get_model(cls) -> str:
        """Selects appropriate model identifier based on the active provider."""
        use_gemini = (
            bool(settings.GEMINI_API_KEY)
            and (not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "dummy_key_for_now")
        )
        if use_gemini:
            # Use gemini-3.6-flash (gemini-2.0-flash was deprecated and retired by Google)
            if settings.LLM_MODEL and "gemini" in settings.LLM_MODEL.lower() and "2.0" not in settings.LLM_MODEL:
                return settings.LLM_MODEL
            return "gemini-3.6-flash"
        return settings.LLM_MODEL

    @classmethod
    async def generate_response(cls, system_prompt: str, user_prompt: str, history: list[dict] = None) -> str:
        """
        Calls the LLM with a system prompt, optional history, and user prompt.
        """
        client = cls.get_client()
        model_name = cls.get_model()
        
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_prompt})
        
        try:
            response = await client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.2,
                max_tokens=4096
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM Generation failed with model '{model_name}': {str(e)}")
            raise

    @classmethod
    async def stream_response(cls, system_prompt: str, user_prompt: str, history: list[dict] = None):
        """
        Streams LLM response token-by-token using Server-Sent Events.
        Yields raw text chunks as they arrive from the API.
        """
        client = cls.get_client()
        model_name = cls.get_model()

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_prompt})

        try:
            stream = await client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.2,
                max_tokens=4096,
                stream=True
            )
            async for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta
        except Exception as e:
            logger.error(f"LLM Streaming failed with model '{model_name}': {str(e)}")
            raise
