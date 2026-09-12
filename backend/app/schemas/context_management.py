"""Pydantic schemas for conversation context management and window optimization."""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

from app.schemas.chat import Message


class OptimizeContextRequest(BaseModel):
    """Request to optimize a multi-turn conversation context window."""

    messages: list[Message] = Field(..., min_length=1, description="Full conversation history.")
    max_context_tokens: Optional[int] = Field(
        default=3000,
        ge=10,
        description="Target maximum token budget for the active prompt context.",
    )
    recent_messages_count: Optional[int] = Field(
        default=4,
        ge=1,
        description="Number of most recent messages to strictly preserve uncompressed.",
    )
    preserve_system: bool = Field(
        default=True,
        description="Whether to preserve system instruction messages verbatim.",
    )
    archive_to_ccr: bool = Field(
        default=True,
        description="Whether to archive compressed older turns to CCR storage for future retrieval.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "messages": [
                        {"role": "system", "content": "You are a backend architectural assistant."},
                        {"role": "user", "content": "Step 1: How should we design the database schema?"},
                        {"role": "assistant", "content": "Use SQLite with SQLAlchemy async models for tables..."},
                        {"role": "user", "content": "Step 2: What about caching and CCR storage?"},
                        {"role": "assistant", "content": "We can build a CCR table with unique context tokens..."},
                        {"role": "user", "content": "Step 3: Now let's implement the context manager window."},
                    ],
                    "max_context_tokens": 150,
                    "recent_messages_count": 2,
                    "preserve_system": True,
                    "archive_to_ccr": True,
                }
            ]
        }
    }


class OptimizationMetrics(BaseModel):
    """Token and message savings metrics after context window optimization."""

    original_message_count: int
    optimized_message_count: int
    original_tokens: int
    optimized_tokens: int
    tokens_saved: int
    compression_ratio: float
    summary_injected: bool
    archived_context_id: Optional[str] = None


class OptimizeContextResponse(BaseModel):
    """Response containing the optimized message list and detailed metrics."""

    optimized_messages: list[Message] = Field(
        ...,
        description="The optimized message list ready to be sent to Gemini.",
    )
    metrics: OptimizationMetrics
    metadata: dict[str, Any] = Field(default_factory=dict)
