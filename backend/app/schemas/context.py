"""Pydantic schemas for Context Storage and CCR (Compress-Cache-Retrieve)."""

from __future__ import annotations

import datetime
import json
from typing import Any, Optional, Union
from pydantic import BaseModel, Field, field_validator


class ContextStoreRequest(BaseModel):
    """Request to store large content in CCR storage with compression."""

    content: Union[str, list[Any], dict[str, Any]] = Field(
        ...,
        description="The raw content, JSON object, or list to compress and cache.",
    )
    content_type: Optional[str] = Field(
        default=None,
        description="Optional explicit content type (e.g. 'json', 'code', 'logs'). Auto-detected if omitted.",
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional human-readable description or tag for this context.",
    )
    options: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional compression options (e.g. max_representatives, max_anomalies).",
    )

    @field_validator("content", mode="before")
    @classmethod
    def coerce_content_to_str(cls, v: Any) -> str:
        if isinstance(v, (dict, list)):
            return json.dumps(v)
        if isinstance(v, str):
            if not v.strip():
                raise ValueError("Content cannot be empty.")
            return v
        return str(v)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "content": [
                        {"id": 1, "service": "auth", "latency": 14.2, "status": "active"},
                        {"id": 2, "service": "auth", "latency": 13.9, "status": "active"},
                        {"id": 3, "service": "auth", "latency": 920.0, "status": "FAILED", "error": "Timeout"}
                    ],
                    "description": "Auth service latency metrics",
                    "options": {
                        "max_representatives": 2,
                        "max_anomalies": 2
                    }
                }
            ]
        }
    }


class ContextStoreResponse(BaseModel):
    """Response returned upon storing a compressed context."""

    context_id: str = Field(..., description="Unique reference ID for retrieval (e.g. ctx_abc123).")
    retrieval_reference: str = Field(..., description="Tag suitable to place in Gemini context (e.g. [CCR:ctx_abc123]).")
    content_type: str = Field(..., description="Detected or specified content type.")
    original_size: int = Field(..., description="Original byte length.")
    compressed_size: int = Field(..., description="Compressed byte length.")
    compression_ratio: float = Field(..., description="compressed_size / original_size.")
    estimated_tokens_saved: int = Field(..., description="Estimated token count reduction.")
    compressed_content: str = Field(..., description="Compressed representation to pass to Gemini.")
    created_at: datetime.datetime = Field(..., description="Timestamp created.")


class ContextDetailResponse(BaseModel):
    """Full detail of a stored context record."""

    context_id: str
    content_type: str
    description: Optional[str] = None
    original_size: int
    compressed_size: int
    compression_ratio: float
    estimated_tokens_before: int
    estimated_tokens_after: int
    estimated_tokens_saved: int
    access_count: int
    created_at: datetime.datetime
    accessed_at: datetime.datetime
    compressed_content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContextRetrieveResponse(BaseModel):
    """Original verbatim content retrieved on demand."""

    context_id: str
    content_type: str
    description: Optional[str] = None
    original_content: str
    original_size: int
    access_count: int
    accessed_at: datetime.datetime


class ContextListResponse(BaseModel):
    """Paginated list of stored contexts."""

    total: int
    items: list[ContextDetailResponse]
