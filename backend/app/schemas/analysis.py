"""Pydantic schemas for the token analysis endpoint."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.chat import Message


# ── Request ──────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    """Incoming request to analyze token usage."""
    messages: list[Message] = Field(..., min_length=1)
    model: str = Field(default="gemini-3.6-flash")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "messages": [
                        {"role": "system", "content": "You are a helpful tutor."},
                        {"role": "user", "content": "What is a decorator in Python?"},
                    ],
                    "model": "gemini-3.6-flash",
                }
            ]
        }
    }


# ── Response ─────────────────────────────────────────────────────────

class MessageAnalysis(BaseModel):
    """Per-message breakdown."""
    index: int
    role: str
    char_count: int
    word_count: int
    estimated_tokens: int
    content_preview: str = Field(description="First 80 chars of the message")


class RoleDistribution(BaseModel):
    """How many messages per role."""
    role: str
    count: int
    total_estimated_tokens: int


class ContentSection(BaseModel):
    """Identifies the largest content chunks."""
    index: int
    role: str
    estimated_tokens: int
    percentage_of_total: float


class AnalyzeResponse(BaseModel):
    """Full analysis result returned to the caller."""
    # Totals
    total_messages: int
    total_characters: int
    total_words: int
    total_estimated_tokens: int

    # Breakdown
    messages: list[MessageAnalysis]
    role_distribution: list[RoleDistribution]
    largest_sections: list[ContentSection] = Field(
        description="Top content sections by estimated token count"
    )

    # Context
    avg_message_tokens: float
    max_message_tokens: int
    min_message_tokens: int

    # Note
    estimation_method: str = Field(
        default="heuristic",
        description="Token counts are estimates, not exact Gemini counts",
    )
