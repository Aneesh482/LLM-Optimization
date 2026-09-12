"""Request logging and metrics service — writes every LLM call to SQLite and aggregates telemetry."""

from __future__ import annotations

import datetime
import logging
from typing import Any, Optional
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.request_log import RequestLog
from app.models.context import ContextRecord

logger = logging.getLogger(__name__)


async def log_request(
    session: AsyncSession,
    *,
    request_id: str,
    model: str,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_tokens: int | None = None,
    latency_ms: float | None = None,
    status: str = "success",
    error_message: str | None = None,
) -> RequestLog:
    """Persist one request log row and return it."""
    entry = RequestLog(
        request_id=request_id,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        latency_ms=latency_ms,
        status=status,
        error_message=error_message,
    )
    session.add(entry)
    await session.commit()
    logger.info(
        "Logged request %s → model=%s status=%s latency=%.0fms",
        request_id,
        model,
        status,
        latency_ms or 0,
    )
    return entry


async def list_requests(
    session: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
    model: Optional[str] = None,
    status: Optional[str] = None,
) -> tuple[int, list[RequestLog]]:
    """List request logs with optional filtering and pagination."""
    query = select(RequestLog)
    count_query = select(func.count(RequestLog.id))

    if model:
        query = query.where(RequestLog.model == model)
        count_query = count_query.where(RequestLog.model == model)
    if status:
        query = query.where(RequestLog.status == status)
        count_query = count_query.where(RequestLog.status == status)

    count_res = await session.execute(count_query)
    total = count_res.scalar_one()

    query = query.order_by(desc(RequestLog.timestamp)).offset(offset).limit(limit)
    res = await session.execute(query)
    items = list(res.scalars().all())

    return total, items


async def get_dashboard_metrics(session: AsyncSession) -> dict[str, Any]:
    """Calculate aggregated gateway telemetry across request logs and CCR context records."""
    # 1. Total & Success/Error Requests
    total_req_res = await session.execute(select(func.count(RequestLog.id)))
    total_requests = total_req_res.scalar_one() or 0

    succ_res = await session.execute(
        select(func.count(RequestLog.id)).where(RequestLog.status == "success")
    )
    successful_requests = succ_res.scalar_one() or 0
    failed_requests = total_requests - successful_requests

    # 2. Token Sums & Latency
    token_stats_stmt = select(
        func.sum(RequestLog.input_tokens),
        func.sum(RequestLog.output_tokens),
        func.sum(RequestLog.total_tokens),
        func.avg(RequestLog.latency_ms),
    ).where(RequestLog.status == "success")
    
    token_stats = await session.execute(token_stats_stmt)
    in_tokens, out_tokens, tot_tokens, avg_lat = token_stats.one()
    total_input = int(in_tokens or 0)
    total_output = int(out_tokens or 0)
    total_tokens = int(tot_tokens or 0)
    avg_latency = float(avg_lat or 0.0)

    # 3. Context & Compression Savings
    ccr_stats_stmt = select(
        func.count(ContextRecord.id),
        func.sum(ContextRecord.estimated_tokens_saved),
        func.avg(ContextRecord.compression_ratio),
    )
    ccr_stats = await session.execute(ccr_stats_stmt)
    total_ctx, tokens_saved, avg_ratio = ccr_stats.one()
    total_tokens_saved = int(tokens_saved or 0)
    avg_compression_ratio = float(avg_ratio or 1.0) if total_ctx else 1.0

    # 4. Pricing Estimates (Standard Gemini Flash Tier: ~$0.075 / 1M input, ~$0.30 / 1M output)
    est_cost = (total_input * 0.075 / 1_000_000.0) + (total_output * 0.30 / 1_000_000.0)
    est_cost_saved = total_tokens_saved * 0.075 / 1_000_000.0

    # 5. Model Breakdown
    model_stats_stmt = (
        select(
            RequestLog.model,
            func.count(RequestLog.id),
            func.sum(RequestLog.total_tokens),
            func.avg(RequestLog.latency_ms),
        )
        .group_by(RequestLog.model)
        .order_by(desc(func.count(RequestLog.id)))
    )
    model_res = await session.execute(model_stats_stmt)
    models_usage = [
        {
            "model": row[0],
            "request_count": int(row[1] or 0),
            "total_tokens": int(row[2] or 0),
            "avg_latency_ms": round(float(row[3] or 0.0), 2),
        }
        for row in model_res.all()
    ]

    # 6. Content Types Breakdown (from CCR Context Records)
    content_stats_stmt = (
        select(
            ContextRecord.content_type,
            func.count(ContextRecord.id),
            func.sum(ContextRecord.original_size),
            func.sum(ContextRecord.compressed_size),
            func.sum(ContextRecord.estimated_tokens_saved),
            func.avg(ContextRecord.compression_ratio),
        )
        .group_by(ContextRecord.content_type)
        .order_by(desc(func.count(ContextRecord.id)))
    )
    content_res = await session.execute(content_stats_stmt)
    content_types_breakdown = [
        {
            "content_type": row[0],
            "count": int(row[1] or 0),
            "total_original_bytes": int(row[2] or 0),
            "total_compressed_bytes": int(row[3] or 0),
            "total_tokens_saved": int(row[4] or 0),
            "avg_compression_ratio": round(float(row[5] or 1.0), 4),
        }
        for row in content_res.all()
    ]

    # 7. Recent Request Time Series (last 20 requests bucketed or sequence)
    recent_stmt = (
        select(RequestLog)
        .order_by(desc(RequestLog.timestamp))
        .limit(30)
    )
    recent_res = await session.execute(recent_stmt)
    recent_logs = list(reversed(recent_res.scalars().all()))

    time_series = []
    for log in recent_logs:
        time_str = log.timestamp.strftime("%H:%M:%S") if log.timestamp else "N/A"
        time_series.append({
            "timestamp": time_str,
            "requests": 1,
            "input_tokens": log.input_tokens or 0,
            "output_tokens": log.output_tokens or 0,
            "tokens_saved": 0,
            "avg_latency_ms": round(log.latency_ms or 0.0, 2),
        })

    return {
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "failed_requests": failed_requests,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_tokens": total_tokens,
        "total_tokens_saved": total_tokens_saved,
        "avg_latency_ms": round(avg_latency, 2),
        "avg_compression_ratio": round(avg_compression_ratio, 4),
        "estimated_cost_usd": round(est_cost, 6),
        "estimated_cost_saved_usd": round(est_cost_saved, 6),
        "models_usage": models_usage,
        "content_types_breakdown": content_types_breakdown,
        "time_series": time_series,
    }
