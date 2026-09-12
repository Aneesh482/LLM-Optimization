"""Pydantic schemas for Provider Context Caching and Multi-Tier Cache Management."""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

from app.schemas.chat import Message


class CreateProviderCacheRequest(BaseModel):
    """Request to create a server-side context cache at Gemini / provider."""

    messages: list[Message] = Field(..., min_length=1, description="Context messages/documents to cache.")
    model: Optional[str] = Field(default="gemini-3.6-flash", description="Model identifier.")
    ttl_seconds: int = Field(default=300, ge=60, le=86400, description="Time to live in seconds (default 300s).")
    display_name: Optional[str] = Field(default=None, description="Human-readable cache name.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "model": "gemini-3.6-flash",
                    "display_name": "API Documentation & Specifications",
                    "ttl_seconds": 600,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a specialized technical assistant with full access to the API Reference documentation."
                        },
                        {
                            "role": "user",
                            "content": "API Reference Document:\nEndpoint /v1/users supports GET, POST, DELETE. Query params include limit, offset, filter..."
                        }
                    ]
                }
            ]
        }
    }


class ProviderCacheResponse(BaseModel):
    """Details of a server-side context cache."""

    name: str = Field(..., description="Provider cache resource identifier (e.g. cachedContents/12345).")
    model: str
    display_name: Optional[str] = None
    expire_time: Optional[str] = None
    cached_tokens: Optional[int] = None


class ProviderCacheListResponse(BaseModel):
    """List of active provider context caches."""

    total: int
    items: list[ProviderCacheResponse]


class CacheHierarchyStatus(BaseModel):
    """Multi-tier caching breakdown across Gateway and Provider."""

    tier_1_in_memory_gateway_cache: dict[str, Any] = Field(
        description="Tier 1: Fast local in-memory response cache for identical queries."
    )
    tier_2_ccr_sqlite_storage: dict[str, Any] = Field(
        description="Tier 2: Compressed context references stored in SQLite with on-demand retrieval."
    )
    tier_3_provider_context_caching: dict[str, Any] = Field(
        description="Tier 3: Gemini server-side context caching reducing prompt token costs and latency."
    )
