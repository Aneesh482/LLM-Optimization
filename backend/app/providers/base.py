"""Abstract base class for LLM providers.

Every concrete provider (Gemini, future OpenAI, etc.) implements this
interface so the rest of the gateway never imports provider-specific code.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class CacheHandle:
    """Provider-side context cache handle."""
    name: str
    model: str
    display_name: Optional[str] = None
    expire_time: Optional[str] = None
    cached_tokens: Optional[int] = None
    raw: dict = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Provider-agnostic response container."""
    content: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cached_tokens: Optional[int] = None
    model: str = ""
    raw: dict = field(default_factory=dict)


class LLMProvider(abc.ABC):
    """Interface that every LLM provider must implement."""

    @abc.abstractmethod
    async def generate(
        self,
        *,
        messages: list[dict],
        model: str,
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
        cached_content: Optional[str] = None,
    ) -> LLMResponse:
        """Send messages to the LLM and return a normalised response."""
        ...

    @abc.abstractmethod
    async def list_models(self) -> list[str]:
        """Return the models this provider supports."""
        ...

    @abc.abstractmethod
    def provider_name(self) -> str:
        """Human-readable name, e.g. 'gemini'."""
        ...

    # ── Provider-Side Context Caching Interface ───────────────────────

    async def create_context_cache(
        self,
        *,
        messages: list[dict],
        model: str,
        ttl_seconds: int = 300,
        display_name: Optional[str] = None,
    ) -> CacheHandle:
        """Create a server-side context cache at the provider."""
        raise NotImplementedError(f"Context caching is not supported by {self.provider_name()}.")

    async def get_context_cache(self, *, cache_name: str) -> Optional[CacheHandle]:
        """Retrieve metadata for a server-side context cache."""
        raise NotImplementedError(f"Context caching is not supported by {self.provider_name()}.")

    async def list_context_caches(self) -> list[CacheHandle]:
        """List active server-side context caches."""
        raise NotImplementedError(f"Context caching is not supported by {self.provider_name()}.")

    async def delete_context_cache(self, *, cache_name: str) -> bool:
        """Delete a server-side context cache."""
        raise NotImplementedError(f"Context caching is not supported by {self.provider_name()}.")
