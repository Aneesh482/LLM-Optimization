"""Multi-Tier Cache Management Service for LLM Context & Provider Caching.

Architecture
------------
Tier 1: Application-Level In-Memory Prompt Cache
        - Deterministic response caching for repeated identical queries.
Tier 2: CCR Storage (SQLite)
        - Persistent large-context archiving with unique context references ([CCR:ctx_xxx]).
Tier 3: Provider-Side Context Caching (Google Gemini API)
        - Server-side cached content (cachedContents/...) reducing prompt token billing and latency.
"""

from __future__ import annotations

import time
import hashlib
import logging
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.providers.base import LLMProvider, CacheHandle
from app.models.database import async_session
from app.services.ccr_service import ccr_service

logger = logging.getLogger(__name__)


class ApplicationMemoryCache:
    """Tier 1: In-memory exact-match response cache."""

    def __init__(self, max_entries: int = 200, default_ttl: int = 300) -> None:
        self._cache: dict[str, tuple[float, Any]] = {}
        self.max_entries = max_entries
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            exp, val = self._cache[key]
            if time.time() < exp:
                self.hits += 1
                return val
            del self._cache[key]
        self.misses += 1
        return None

    def set(self, key: str, val: Any, ttl: Optional[int] = None) -> None:
        if len(self._cache) >= self.max_entries:
            # Evict oldest entry
            oldest = min(self._cache.keys(), key=lambda k: self._cache[k][0], default=None)
            if oldest:
                del self._cache[oldest]
        exp = time.time() + (ttl or self.default_ttl)
        self._cache[key] = (exp, val)

    def stats(self) -> dict[str, Any]:
        valid_count = sum(1 for exp, _ in self._cache.values() if time.time() < exp)
        return {
            "cached_entries": valid_count,
            "max_capacity": self.max_entries,
            "cache_hits": self.hits,
            "cache_misses": self.misses,
            "hit_ratio": round(self.hits / max(1, self.hits + self.misses), 3),
        }


class CacheService:
    """Coordinates Tier 1, Tier 2 (CCR), and Tier 3 (Gemini) caching systems."""

    def __init__(self) -> None:
        self.memory_cache = ApplicationMemoryCache()

    @staticmethod
    def generate_cache_key(model: str, messages: list[dict], temperature: Optional[float] = None) -> str:
        """Create a deterministic hash key for prompt completions."""
        payload = f"{model}:{temperature}:" + "|".join(
            f"{m.get('role')}:{m.get('content')}" for m in messages
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    async def get_hierarchy_status(
        self,
        db: AsyncSession,
        provider: Optional[LLMProvider] = None,
    ) -> dict[str, Any]:
        """Return the multi-tier caching status breakdown."""
        # Tier 1 Stats
        t1_stats = self.memory_cache.stats()

        # Tier 2 (CCR SQLite) Stats
        total_ccr, _ = await ccr_service.list_contexts(db, limit=1)
        t2_stats = {
            "stored_contexts": total_ccr,
            "storage_backend": "sqlite",
            "lifecycle": "on-demand compressed storage",
        }

        # Tier 3 (Provider / Gemini) Stats
        t3_stats: dict[str, Any] = {
            "provider": provider.provider_name() if provider else "unknown",
            "supported": True,
            "active_provider_caches": 0,
            "caches": [],
        }

        if provider:
            try:
                caches = await provider.list_context_caches()
                t3_stats["active_provider_caches"] = len(caches)
                t3_stats["caches"] = [
                    {
                        "name": c.name,
                        "model": c.model,
                        "display_name": c.display_name,
                        "expire_time": c.expire_time,
                        "cached_tokens": c.cached_tokens,
                    }
                    for c in caches
                ]
            except Exception as exc:
                t3_stats["error"] = str(exc)

        return {
            "tier_1_in_memory_gateway_cache": t1_stats,
            "tier_2_ccr_sqlite_storage": t2_stats,
            "tier_3_provider_context_caching": t3_stats,
        }


# Singleton
cache_service = CacheService()
