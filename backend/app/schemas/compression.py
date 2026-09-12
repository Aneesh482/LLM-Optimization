"""Pydantic schemas for content compression requests and responses."""

from __future__ import annotations

import json
from typing import Any, Optional, Union
from pydantic import BaseModel, Field, field_validator


class CompressRequest(BaseModel):
    """Generic request to compress content (auto-detected or explicit)."""

    content: Union[str, list[Any], dict[str, Any]] = Field(
        ...,
        description="The raw content, source code, logs, or JSON object/array to compress.",
    )
    content_type: Optional[str] = Field(
        default=None,
        description="Optional explicit content type ('json', 'code', 'logs'). Auto-detected if omitted.",
    )
    options: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional compressor parameters.",
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
                    "content": "def calculate_total(items):\n    sum = 0\n    for item in items:\n        sum += item.price\n    return sum",
                    "content_type": "code",
                    "options": {"skeleton_only": True}
                }
            ]
        }
    }


class CompressJSONRequest(BaseModel):
    """Request schema tailored for SmartCrusher-style JSON compression."""

    content: Union[list[Any], dict[str, Any], str] = Field(
        ...,
        description="JSON array of records or dictionary to compress.",
    )
    options: Optional[dict[str, Any]] = Field(
        default_factory=lambda: {"max_representatives": 2, "max_anomalies": 3},
        description="Compression options (e.g. max_representatives, max_anomalies, min_records_for_compression).",
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
                        {"id": 1, "service": "auth", "status": "active", "latency_ms": 12.4},
                        {"id": 2, "service": "auth", "status": "active", "latency_ms": 14.1},
                        {"id": 3, "service": "auth", "status": "active", "latency_ms": 13.8},
                        {"id": 4, "service": "auth", "status": "active", "latency_ms": 15.0},
                        {"id": 5, "service": "auth", "status": "active", "latency_ms": 14.2},
                        {"id": 6, "service": "auth", "status": "active", "latency_ms": 13.9},
                        {"id": 7, "service": "auth", "status": "active", "latency_ms": 14.5},
                        {"id": 8, "service": "auth", "status": "active", "latency_ms": 13.7},
                        {"id": 9, "service": "auth", "status": "active", "latency_ms": 14.9},
                        {"id": 10, "service": "auth", "status": "active", "latency_ms": 15.2},
                        {"id": 99, "service": "auth", "status": "FAILED", "latency_ms": 940.0, "error": "Timeout"}
                    ],
                    "options": {
                        "max_representatives": 2,
                        "max_anomalies": 2
                    }
                }
            ]
        }
    }


class CompressCodeRequest(BaseModel):
    """Request schema tailored for Source Code compression."""

    content: str = Field(
        ...,
        min_length=1,
        description="Source code string (Python, TypeScript, Go, Java, Rust, SQL, etc.).",
    )
    language: Optional[str] = Field(
        default=None,
        description="Optional language hint (e.g. 'python', 'javascript', 'go', 'rust'). Auto-detected if omitted.",
    )
    options: Optional[dict[str, Any]] = Field(
        default_factory=lambda: {"skeleton_only": True, "preserve_docstrings": True},
        description="Compression options (skeleton_only, preserve_docstrings, min_lines).",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "content": "\"\"\"User management module.\"\"\"\nimport os\nfrom typing import Optional, List\n\nclass UserManager:\n    \"\"\"Handles user authentication and active tokens.\"\"\"\n    def __init__(self, db_url: str) -> None:\n        self.db_url = db_url\n        self.cache = {}\n        for i in range(500):\n            self.cache[i] = f\"init_{i}\"\n\n    async def authenticate(self, username: str, password_hash: str) -> bool:\n        \"\"\"Verify user credentials.\"\"\"\n        if not username:\n            return False\n        return True\n\n    def logout(self, user_id: str) -> None:\n        self.cache.pop(user_id, None)",
                    "language": "python",
                    "options": {
                        "skeleton_only": True,
                        "preserve_docstrings": True
                    }
                }
            ]
        }
    }


class CompressLogsRequest(BaseModel):
    """Request schema tailored for Log Stream compression."""

    content: str = Field(
        ...,
        min_length=1,
        description="Multi-line log stream text.",
    )
    options: Optional[dict[str, Any]] = Field(
        default_factory=lambda: {"repeat_threshold": 3, "preserve_all_errors": True},
        description="Compression options (repeat_threshold, preserve_all_errors, min_lines).",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "content": "2026-09-09T12:00:01 INFO 10.0.0.1 GET /health 200 latency=1.2ms\n2026-09-09T12:00:02 INFO 10.0.0.2 GET /health 200 latency=1.1ms\n2026-09-09T12:00:03 INFO 10.0.0.3 GET /health 200 latency=1.4ms\n2026-09-09T12:00:04 INFO 10.0.0.4 GET /health 200 latency=1.0ms\n2026-09-09T12:00:05 INFO 10.0.0.5 GET /health 200 latency=1.3ms\n2026-09-09T12:00:06 INFO 10.0.0.6 GET /health 200 latency=1.5ms\n2026-09-09T12:00:07 INFO 10.0.0.7 GET /health 200 latency=1.1ms\n2026-09-09T12:00:08 INFO 10.0.0.8 GET /health 200 latency=1.2ms\n2026-09-09T12:00:09 INFO 10.0.0.9 GET /health 200 latency=1.0ms\n2026-09-09T12:00:10 INFO 10.0.0.10 GET /health 200 latency=1.3ms\n2026-09-09T12:00:11 ERROR 10.0.0.15 Database connection pool exhausted: TimeoutError\n2026-09-09T12:00:12 INFO 10.0.0.11 GET /health 200 latency=1.2ms\n2026-09-09T12:00:13 INFO 10.0.0.12 GET /health 200 latency=1.1ms\n2026-09-09T12:00:14 INFO 10.0.0.13 GET /health 200 latency=1.4ms",
                    "options": {
                        "repeat_threshold": 3,
                        "preserve_all_errors": True
                    }
                }
            ]
        }
    }


class CompressResponse(BaseModel):
    """Normalized response reporting compression outcome and metrics."""

    content_type: str = Field(..., description="Content type handled (e.g. 'json', 'code', 'logs').")
    original_size: int = Field(..., description="Original size in bytes.")
    compressed_size: int = Field(..., description="Compressed size in bytes.")
    compression_ratio: float = Field(..., description="compressed_size / original_size.")
    estimated_tokens_before: int = Field(..., description="Estimated token count before compression.")
    estimated_tokens_after: int = Field(..., description="Estimated token count after compression.")
    estimated_tokens_saved: int = Field(..., description="Estimated tokens saved.")
    compressed_content: str = Field(..., description="The compressed text or JSON representation.")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional compressor metadata (schema info, anomaly count, language, line counts, etc.).",
    )
