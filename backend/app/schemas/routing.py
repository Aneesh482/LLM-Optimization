"""Pydantic schemas for the content routing endpoint."""

import json
from typing import Any, Union
from pydantic import BaseModel, Field, field_validator

from app.schemas.chat import Message


# ── Request ──────────────────────────────────────────────────────────

class RouteRequest(BaseModel):
    """Incoming request to detect content types."""
    messages: list[Message] = Field(..., min_length=1)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "messages": [
                        {"role": "user", "content": '{"users": [{"id": 1}, {"id": 2}]}'},
                        {"role": "user", "content": "def hello():\n    return 'hi'"},
                    ]
                }
            ]
        }
    }


class RouteContentRequest(BaseModel):
    """Route a single piece of raw content (no role wrapper)."""
    content: Union[str, list[Any], dict[str, Any]] = Field(
        ...,
        description="The raw text, or direct JSON object/array to detect.",
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
                {"content": {"status": 200, "data": [1, 2, 3]}}
            ]
        }
    }


# ── Response ─────────────────────────────────────────────────────────

class TypeDistribution(BaseModel):
    """How many messages map to each content type."""
    content_type: str
    count: int


class MessageRouting(BaseModel):
    """Routing result for a single message."""
    index: int
    role: str
    content_type: str
    confidence: float
    scores: dict[str, float]
    content_preview: str = Field(description="First 80 chars of the message")


class RouteResponse(BaseModel):
    """Full routing result for a batch of messages."""
    total_messages: int
    type_distribution: list[TypeDistribution]
    messages: list[MessageRouting]


class SingleRouteResponse(BaseModel):
    """Routing result for a single piece of content."""
    content_type: str
    confidence: float
    scores: dict[str, float]
    metadata: dict[str, object] = Field(default_factory=dict)
    content_preview: str = Field(description="First 80 chars of the content")
