

from __future__ import annotations

import logging
from typing import Optional

from google import genai
from google.genai import types

from app.providers.base import LLMProvider, LLMResponse, CacheHandle
from app.config import settings

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Talks to Google Gemini via the google-genai SDK."""

    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or settings.gemini_api_key
        if not key:
            raise ValueError(
                "GEMINI_API_KEY is not set. "
                "Add it to your .env file or pass it explicitly."
            )
        self._client = genai.Client(api_key=key)

    # ── public interface ─────────────────────────────────────────────

    def provider_name(self) -> str:
        return "gemini"

    async def generate(
        self,
        *,
        messages: list[dict],
        model: str,
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
        cached_content: Optional[str] = None,
    ) -> LLMResponse:
        """Send a request to Gemini and return a normalised LLMResponse."""

        model_id = model or settings.default_model

        # Separate system instruction from conversation turns.
        system_instruction, contents = self._prepare_contents(messages)

        # Build generation config with optional provider-side cached content.
        gen_config = self._build_gen_config(temperature, max_output_tokens, cached_content)

        logger.info(
            "Gemini request → model=%s messages=%d cached_content=%s",
            model_id,
            len(contents),
            cached_content or "none",
        )

        response = await self._call_gemini(
            model_id=model_id,
            contents=contents,
            system_instruction=system_instruction,
            gen_config=gen_config,
        )

        return self._parse_response(response, model_id)

    async def list_models(self) -> list[str]:
        """Return available Gemini model ids."""
        result: list[str] = []
        async for model in self._client.aio.models.list():
            if model.name:
                result.append(model.name)
        return result

    # ── Gemini Context Caching Implementation ─────────────────────────

    async def create_context_cache(
        self,
        *,
        messages: list[dict],
        model: str,
        ttl_seconds: int = 300,
        display_name: Optional[str] = None,
    ) -> CacheHandle:
        """Create a server-side context cache in Gemini."""
        model_id = model or settings.default_model
        system_instruction, contents = self._prepare_contents(messages)

        config = types.CreateCachedContentConfig(
            contents=contents,
            system_instruction=system_instruction,
            ttl=f"{ttl_seconds}s",
            display_name=display_name,
        )

        cache_obj = await self._client.aio.caches.create(
            model=model_id,
            config=config,
        )

        cached_tokens = getattr(cache_obj, "usage_metadata", None)
        token_count = getattr(cached_tokens, "total_token_count", None) if cached_tokens else None

        return CacheHandle(
            name=cache_obj.name,
            model=cache_obj.model or model_id,
            display_name=getattr(cache_obj, "display_name", None),
            expire_time=str(getattr(cache_obj, "expire_time", "")),
            cached_tokens=token_count,
            raw={"name": cache_obj.name, "model": cache_obj.model},
        )

    async def get_context_cache(self, *, cache_name: str) -> Optional[CacheHandle]:
        """Fetch metadata for an existing Gemini context cache."""
        try:
            cache_obj = await self._client.aio.caches.get(name=cache_name)
            cached_tokens = getattr(cache_obj, "usage_metadata", None)
            token_count = getattr(cached_tokens, "total_token_count", None) if cached_tokens else None
            return CacheHandle(
                name=cache_obj.name,
                model=cache_obj.model or "",
                display_name=getattr(cache_obj, "display_name", None),
                expire_time=str(getattr(cache_obj, "expire_time", "")),
                cached_tokens=token_count,
            )
        except Exception as exc:
            logger.warning("Failed to get cache %s: %s", cache_name, exc)
            return None

    async def list_context_caches(self) -> list[CacheHandle]:
        """List active Gemini context caches."""
        result: list[CacheHandle] = []
        try:
            pager = await self._client.aio.caches.list()
            async for cache_obj in pager:
                cached_tokens = getattr(cache_obj, "usage_metadata", None)
                token_count = getattr(cached_tokens, "total_token_count", None) if cached_tokens else None
                result.append(
                    CacheHandle(
                        name=cache_obj.name,
                        model=cache_obj.model or "",
                        display_name=getattr(cache_obj, "display_name", None),
                        expire_time=str(getattr(cache_obj, "expire_time", "")),
                        cached_tokens=token_count,
                    )
                )
        except Exception as exc:
            logger.warning("Failed to list Gemini caches: %s", exc)
        return result

    async def delete_context_cache(self, *, cache_name: str) -> bool:
        """Delete an active Gemini context cache."""
        try:
            await self._client.aio.caches.delete(name=cache_name)
            return True
        except Exception as exc:
            logger.warning("Failed to delete cache %s: %s", cache_name, exc)
            return False

    # ── internals ────────────────────────────────────────────────────

    @staticmethod
    def _prepare_contents(
        messages: list[dict],
    ) -> tuple[str | None, list[types.Content]]:
        """Convert our generic message list into Gemini content objects."""
        system_parts: list[str] = []
        contents: list[types.Content] = []

        for msg in messages:
            role = msg["role"]
            text = msg["content"]

            if role == "system":
                system_parts.append(text)
            else:
                gemini_role = "model" if role == "assistant" else "user"
                contents.append(
                    types.Content(
                        role=gemini_role,
                        parts=[types.Part.from_text(text=text)],
                    )
                )

        system_instruction = "\n".join(system_parts) if system_parts else None
        return system_instruction, contents

    @staticmethod
    def _build_gen_config(
        temperature: Optional[float],
        max_output_tokens: Optional[int],
        cached_content: Optional[str] = None,
    ) -> types.GenerateContentConfig:
        """Build a Gemini GenerateContentConfig with optional cached content."""
        kwargs: dict = {}
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_output_tokens is not None:
            kwargs["max_output_tokens"] = max_output_tokens
        if cached_content:
            kwargs["cached_content"] = cached_content
        return types.GenerateContentConfig(**kwargs)

    async def _call_gemini(
        self,
        *,
        model_id: str,
        contents: list[types.Content],
        system_instruction: str | None,
        gen_config: types.GenerateContentConfig,
    ):
        """Actual async SDK call, isolated for easy mocking."""
        if system_instruction and not getattr(gen_config, "cached_content", None):
            gen_config.system_instruction = system_instruction

        response = await self._client.aio.models.generate_content(
            model=model_id,
            contents=contents,
            config=gen_config,
        )
        return response

    @staticmethod
    def _parse_response(response, model_id: str) -> LLMResponse:
        """Extract text and usage metadata (including cached tokens) from the SDK response."""
        text = response.text or ""

        input_tokens: int | None = None
        output_tokens: int | None = None
        total_tokens: int | None = None
        cached_tokens: int | None = None

        usage = getattr(response, "usage_metadata", None)
        if usage:
            input_tokens = getattr(usage, "prompt_token_count", None)
            output_tokens = getattr(usage, "candidates_token_count", None)
            cached_tokens = getattr(usage, "cached_content_token_count", None)
            if input_tokens is not None and output_tokens is not None:
                total_tokens = input_tokens + output_tokens

        return LLMResponse(
            content=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cached_tokens=cached_tokens,
            model=model_id,
        )
