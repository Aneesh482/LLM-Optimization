"""Pydantic schemas for chat completion requests and responses."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ── Request ──────────────────────────────────────────────────────────

class Message(BaseModel):
    """A single message in the conversation."""
    role: str = Field(..., description="One of: system, user, assistant")
    content: str = Field(..., min_length=1, description="Message text")

    model_config = {
        "json_schema_extra": {
            "examples": [{"role": "user", "content": "Explain recursion."}]
        }
    }


class ChatRequest(BaseModel):
    """Incoming request to the gateway."""
    model: str = Field(default="gemini-3.6-flash", description="Gemini model id")
    messages: list[Message] = Field(..., min_length=1, description="Conversation messages")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    optimize_context: bool = Field(default=False, description="Enable automatic conversation context optimization")
    max_context_tokens: Optional[int] = Field(default=None, description="Optional token ceiling for context window")
    cached_content: Optional[str] = Field(default=None, description="Provider-side context cache resource name (e.g. cachedContents/12345)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "model": "gemini-3.6-flash",
                    "messages": [
                        {"role": "user", "content": "Explain recursion in Python."}
                    ],
                    "temperature": 0.7,
                    "optimize_context": False,
                    "cached_content": None,
                }
            ]
        }
    }


# ── Response ─────────────────────────────────────────────────────────

class UsageInfo(BaseModel):
    """Token usage returned by the provider."""
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cached_tokens: Optional[int] = None


class ChatResponse(BaseModel):
    """Normalised response returned to the caller."""
    id: str
    model: str
    content: str
    usage: UsageInfo
    latency_ms: float
    optimization: Optional[dict] = None


# ── Health ───────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    provider: str = "gemini"


# ── Error ────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
