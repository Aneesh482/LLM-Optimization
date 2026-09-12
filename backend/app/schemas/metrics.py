"""Pydantic schemas for telemetry metrics and request logs."""

from __future__ import annotations

import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class RequestLogItem(BaseModel):
    """A single logged LLM request."""
    id: int
    request_id: str
    timestamp: datetime.datetime
    model: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    latency_ms: Optional[float] = None
    status: str
    error_message: Optional[str] = None


class RequestListResponse(BaseModel):
    """Paginated list of request logs."""
    total: int
    items: list[RequestLogItem]


class ModelUsageMetric(BaseModel):
    """Usage counts and token sums per model."""
    model: str
    request_count: int
    total_tokens: int
    avg_latency_ms: float


class ContentTypeMetric(BaseModel):
    """Context storage and compression breakdown per content type."""
    content_type: str
    count: int
    total_original_bytes: int
    total_compressed_bytes: int
    total_tokens_saved: int
    avg_compression_ratio: float


class TimeSeriesDataPoint(BaseModel):
    """Time-series telemetry point."""
    timestamp: str
    requests: int
    input_tokens: int
    output_tokens: int
    tokens_saved: int
    avg_latency_ms: float


class DashboardMetricsResponse(BaseModel):
    """Comprehensive gateway metrics for the React dashboard."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_tokens_saved: int
    avg_latency_ms: float
    avg_compression_ratio: float
    estimated_cost_usd: float
    estimated_cost_saved_usd: float
    models_usage: list[ModelUsageMetric]
    content_types_breakdown: list[ContentTypeMetric]
    time_series: list[TimeSeriesDataPoint]
