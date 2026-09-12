import json
import time
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.chat import (
    Message,
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    HealthResponse,
    UsageInfo,
)
from app.schemas.analysis import AnalyzeRequest, AnalyzeResponse
from app.schemas.routing import (
    RouteRequest,
    RouteContentRequest,
    RouteResponse,
    SingleRouteResponse,
)
from app.schemas.compression import (
    CompressRequest,
    CompressJSONRequest,
    CompressCodeRequest,
    CompressLogsRequest,
    CompressResponse,
)
from app.schemas.context import (
    ContextStoreRequest,
    ContextStoreResponse,
    ContextDetailResponse,
    ContextRetrieveResponse,
    ContextListResponse,
)
from app.schemas.context_management import (
    OptimizeContextRequest,
    OptimizeContextResponse,
    OptimizationMetrics,
)
from app.schemas.cache import (
    CreateProviderCacheRequest,
    ProviderCacheResponse,
    ProviderCacheListResponse,
    CacheHierarchyStatus,
)
from app.schemas.metrics import (
    RequestLogItem,
    RequestListResponse,
    DashboardMetricsResponse,
)
from app.providers.gemini import GeminiProvider
from app.models.database import get_session
from app.services.logging_service import log_request, list_requests, get_dashboard_metrics
from app.services.token_analyzer import analyze_messages
from app.services.content_router import ContentRouter
from app.services.compressors import get_compressor, JSONCompressor
from app.services.ccr_service import ccr_service
from app.services.context_manager import context_manager
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Provider singleton — created once at import time.
# If the key is missing the app still boots (health works),
# but chat completions return a clear error.
_provider: GeminiProvider | None = None

# Content router singleton — stateless, always available.
_content_router = ContentRouter()


def _get_provider() -> GeminiProvider:
    global _provider
    if _provider is None:
        try:
            _provider = GeminiProvider()
        except ValueError as exc:
            raise HTTPException(status_code=503, detail=str(exc))
    return _provider


# ── Health ───────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["Health"], summary="Gateway health check")
async def health():
    return HealthResponse()


# ── Chat completions ─────────────────────────────────────────────────

@router.post(
    "/api/v1/chat/completions",
    response_model=ChatResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    tags=["Chat Completions"],
    summary="Send chat completion via Gemini gateway",
)
async def chat_completions(
    request: ChatRequest,
    db: AsyncSession = Depends(get_session),
):
    """Forward a chat request through the gateway to Gemini."""

    request_id = str(uuid.uuid4())
    provider = _get_provider()
    start = time.perf_counter()

    try:
        messages = [m.model_dump() for m in request.messages]

        opt_metrics = None
        # Automatic Context Management if requested
        if request.optimize_context:
            optimized_msgs, opt_metrics = await context_manager.optimize_context(
                messages,
                max_context_tokens=request.max_context_tokens,
                db=db,
            )
            messages = optimized_msgs

        llm_response = await provider.generate(
            messages=messages,
            model=request.model,
            temperature=request.temperature,
            max_output_tokens=request.max_output_tokens,
            cached_content=request.cached_content,
        )

        latency_ms = (time.perf_counter() - start) * 1000

        # Log to DB
        await log_request(
            db,
            request_id=request_id,
            model=llm_response.model,
            input_tokens=llm_response.input_tokens,
            output_tokens=llm_response.output_tokens,
            total_tokens=llm_response.total_tokens,
            latency_ms=latency_ms,
            status="success",
        )

        return ChatResponse(
            id=request_id,
            model=llm_response.model,
            content=llm_response.content,
            usage=UsageInfo(
                input_tokens=llm_response.input_tokens,
                output_tokens=llm_response.output_tokens,
                total_tokens=llm_response.total_tokens,
                cached_tokens=llm_response.cached_tokens,
            ),
            latency_ms=round(latency_ms, 2),
            optimization=opt_metrics,
        )

    except HTTPException:
        raise  # re-raise provider-missing 503
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        error_msg = str(exc)
        logger.exception("Chat completion failed: %s", error_msg)

        # Log the error
        await log_request(
            db,
            request_id=request_id,
            model=request.model,
            latency_ms=latency_ms,
            status="error",
            error_message=error_msg,
        )

        raise HTTPException(status_code=500, detail=error_msg)


# ── Token analysis ───────────────────────────────────────────────────

@router.post("/api/v1/analyze", response_model=AnalyzeResponse, tags=["Token Analysis"], summary="Analyze message tokens and context metrics")
async def analyze(request: AnalyzeRequest):
    """Analyze token usage and context statistics without calling Gemini."""
    messages = [m.model_dump() for m in request.messages]
    result = analyze_messages(messages)
    return AnalyzeResponse(**result)


# ── Content routing ──────────────────────────────────────────────────

@router.post("/api/v1/route", response_model=RouteResponse, tags=["Content Router"], summary="Route and classify conversation messages")
async def route_messages(request: RouteRequest):
    """Detect content types for each message in a conversation."""
    messages = [m.model_dump() for m in request.messages]
    summary = _content_router.route_summary(messages)
    return RouteResponse(**summary)


@router.post("/api/v1/route/detect", response_model=SingleRouteResponse, tags=["Content Router"], summary="Detect content type of a single snippet")
async def route_single(request: RouteContentRequest):
    """Detect the content type of a single piece of raw content."""
    result = _content_router.detect(request.content)
    return SingleRouteResponse(
        content_type=result.content_type.value,
        confidence=result.confidence,
        scores=result.scores,
        metadata=result.metadata,
        content_preview=request.content[:80],
    )


# ── Compression ──────────────────────────────────────────────────────

@router.post("/api/v1/compress", response_model=CompressResponse, tags=["Compression"], summary="Auto-detect & compress content")
async def compress_content(request: CompressRequest):
    """Compress content using the appropriate content-type compressor.
    
    If content_type is not provided, content router detects it automatically.
    """
    target_type = request.content_type
    if not target_type:
        detection = _content_router.detect(request.content)
        target_type = detection.content_type.value

    compressor = get_compressor(target_type)
    if not compressor:
        # If no specialized compressor exists for this type yet, default to json or verbatim
        compressor = get_compressor("json") if target_type == "json" else None

    if not compressor:
        raise HTTPException(
            status_code=400,
            detail=f"No compressor available for content type '{target_type}'.",
        )

    options = request.options or {}
    result = compressor.compress(request.content, **options)

    return CompressResponse(
        content_type=result.content_type,
        original_size=result.original_size,
        compressed_size=result.compressed_size,
        compression_ratio=result.compression_ratio,
        estimated_tokens_before=result.estimated_tokens_before,
        estimated_tokens_after=result.estimated_tokens_after,
        estimated_tokens_saved=result.estimated_tokens_saved,
        compressed_content=result.compressed_content,
        metadata=result.metadata,
    )


@router.post("/api/v1/compress/json", response_model=CompressResponse, tags=["Compression"], summary="SmartCrusher JSON compression")
async def compress_json_explicit(request: CompressJSONRequest):
    """Explicit endpoint for SmartCrusher-style JSON compression."""
    compressor = JSONCompressor()
    options = request.options or {}
    result = compressor.compress(request.content, **options)

    return CompressResponse(
        content_type="json",
        original_size=result.original_size,
        compressed_size=result.compressed_size,
        compression_ratio=result.compression_ratio,
        estimated_tokens_before=result.estimated_tokens_before,
        estimated_tokens_after=result.estimated_tokens_after,
        estimated_tokens_saved=result.estimated_tokens_saved,
        compressed_content=result.compressed_content,
        metadata=result.metadata,
    )


@router.post("/api/v1/compress/code", response_model=CompressResponse, tags=["Compression"], summary="AST & structure code compression")
async def compress_code_explicit(request: CompressCodeRequest):
    """Explicit endpoint for structure-preserving source code compression."""
    compressor = get_compressor("code")
    options = dict(request.options or {})
    if request.language:
        options["language"] = request.language

    result = compressor.compress(request.content, **options)

    return CompressResponse(
        content_type="code",
        original_size=result.original_size,
        compressed_size=result.compressed_size,
        compression_ratio=result.compression_ratio,
        estimated_tokens_before=result.estimated_tokens_before,
        estimated_tokens_after=result.estimated_tokens_after,
        estimated_tokens_saved=result.estimated_tokens_saved,
        compressed_content=result.compressed_content,
        metadata=result.metadata,
    )


@router.post("/api/v1/compress/logs", response_model=CompressResponse, tags=["Compression"], summary="Template deduplication log compression")
async def compress_logs_explicit(request: CompressLogsRequest):
    """Explicit endpoint for template-deduplicated log stream compression."""
    compressor = get_compressor("logs")
    options = request.options or {}
    result = compressor.compress(request.content, **options)

    return CompressResponse(
        content_type="logs",
        original_size=result.original_size,
        compressed_size=result.compressed_size,
        compression_ratio=result.compression_ratio,
        estimated_tokens_before=result.estimated_tokens_before,
        estimated_tokens_after=result.estimated_tokens_after,
        estimated_tokens_saved=result.estimated_tokens_saved,
        compressed_content=result.compressed_content,
        metadata=result.metadata,
    )



# ── CCR (Compress - Cache - Retrieve) ────────────────────────────────

@router.post("/api/v1/context/store", response_model=ContextStoreResponse, tags=["CCR Storage"], summary="Store & compress large context in SQLite")
async def store_context(
    request: ContextStoreRequest,
    db: AsyncSession = Depends(get_session),
):
    """Compress and store original content in SQLite, returning a CCR reference."""
    record = await ccr_service.store_context(
        db,
        content=request.content,
        content_type=request.content_type,
        description=request.description,
        options=request.options,
    )
    return ContextStoreResponse(
        context_id=record.context_id,
        retrieval_reference=f"[CCR:{record.context_id}]",
        content_type=record.content_type,
        original_size=record.original_size,
        compressed_size=record.compressed_size,
        compression_ratio=record.compression_ratio,
        estimated_tokens_saved=record.estimated_tokens_saved,
        compressed_content=record.compressed_content,
        created_at=record.created_at,
    )


@router.get("/api/v1/context/{context_id}", response_model=ContextDetailResponse, tags=["CCR Storage"], summary="Get stored context details & preview")
async def get_context_detail(
    context_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Fetch metadata and compressed representation of a stored context."""
    record = await ccr_service.get_context(db, context_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Context '{context_id}' not found.")

    meta = json.loads(record.metadata_json) if record.metadata_json else {}
    return ContextDetailResponse(
        context_id=record.context_id,
        content_type=record.content_type,
        description=record.description,
        original_size=record.original_size,
        compressed_size=record.compressed_size,
        compression_ratio=record.compression_ratio,
        estimated_tokens_before=record.estimated_tokens_before,
        estimated_tokens_after=record.estimated_tokens_after,
        estimated_tokens_saved=record.estimated_tokens_saved,
        access_count=record.access_count,
        created_at=record.created_at,
        accessed_at=record.accessed_at,
        compressed_content=record.compressed_content,
        metadata=meta,
    )


@router.post("/api/v1/context/{context_id}/retrieve", response_model=ContextRetrieveResponse, tags=["CCR Storage"], summary="Retrieve raw verbatim original content (POST)")
async def retrieve_original_context_post(
    context_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Retrieve original verbatim content for a context reference."""
    record = await ccr_service.retrieve_original(db, context_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Context '{context_id}' not found.")

    return ContextRetrieveResponse(
        context_id=record.context_id,
        content_type=record.content_type,
        description=record.description,
        original_content=record.original_content,
        original_size=record.original_size,
        access_count=record.access_count,
        accessed_at=record.accessed_at,
    )


@router.get("/api/v1/context/{context_id}/retrieve", response_model=ContextRetrieveResponse, tags=["CCR Storage"], summary="Retrieve raw verbatim original content (GET)")
async def retrieve_original_context_get(
    context_id: str,
    db: AsyncSession = Depends(get_session),
):
    """GET alias for retrieving original verbatim content."""
    record = await ccr_service.retrieve_original(db, context_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Context '{context_id}' not found.")

    return ContextRetrieveResponse(
        context_id=record.context_id,
        content_type=record.content_type,
        description=record.description,
        original_content=record.original_content,
        original_size=record.original_size,
        access_count=record.access_count,
        accessed_at=record.accessed_at,
    )


@router.get("/api/v1/contexts", response_model=ContextListResponse, tags=["CCR Storage"], summary="List stored contexts with pagination")
async def list_contexts(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
):
    """List stored contexts with pagination."""
    total, items = await ccr_service.list_contexts(db, limit=limit, offset=offset)
    res_items = []
    for record in items:
        meta = json.loads(record.metadata_json) if record.metadata_json else {}
        res_items.append(
            ContextDetailResponse(
                context_id=record.context_id,
                content_type=record.content_type,
                description=record.description,
                original_size=record.original_size,
                compressed_size=record.compressed_size,
                compression_ratio=record.compression_ratio,
                estimated_tokens_before=record.estimated_tokens_before,
                estimated_tokens_after=record.estimated_tokens_after,
                estimated_tokens_saved=record.estimated_tokens_saved,
                access_count=record.access_count,
                created_at=record.created_at,
                accessed_at=record.accessed_at,
                compressed_content=record.compressed_content,
                metadata=meta,
            )
        )
    return ContextListResponse(total=total, items=res_items)


# ── Context Window Optimization ──────────────────────────────────────

@router.post("/api/v1/context/optimize", response_model=OptimizeContextResponse, tags=["Context Management"], summary="Optimize conversation context window")
async def optimize_context_endpoint(
    request: OptimizeContextRequest,
    db: AsyncSession = Depends(get_session),
):
    """Optimize a conversation history using rolling windows, summarization, and CCR archiving."""
    messages = [m.model_dump() for m in request.messages]
    opt_msgs, metrics = await context_manager.optimize_context(
        messages,
        max_context_tokens=request.max_context_tokens,
        recent_count=request.recent_messages_count,
        preserve_system=request.preserve_system,
        archive_to_ccr=request.archive_to_ccr,
        db=db,
    )

    opt_pydantic_msgs = [Message(**m) for m in opt_msgs]
    opt_metrics = OptimizationMetrics(
        original_message_count=metrics["original_message_count"],
        optimized_message_count=metrics["optimized_message_count"],
        original_tokens=metrics["original_tokens"],
        optimized_tokens=metrics["optimized_tokens"],
        tokens_saved=metrics["tokens_saved"],
        compression_ratio=metrics["compression_ratio"],
        summary_injected=metrics["summary_injected"],
        archived_context_id=metrics.get("archived_context_id"),
    )

    return OptimizeContextResponse(
        optimized_messages=opt_pydantic_msgs,
        metrics=opt_metrics,
        metadata=metrics,
    )


# ── Provider-Side Context Caching (Gemini) ───────────────────────────

@router.post("/api/v1/cache/provider/create", response_model=ProviderCacheResponse, tags=["Phase 8: Cache & Provider Optimization"], summary="Create Gemini server-side context cache")
async def create_provider_cache(request: CreateProviderCacheRequest):
    """Create a server-side context cache at Gemini to reduce prompt token costs."""
    provider = _get_provider()
    messages = [m.model_dump() for m in request.messages]
    try:
        handle = await provider.create_context_cache(
            messages=messages,
            model=request.model or "gemini-3.6-flash",
            ttl_seconds=request.ttl_seconds,
            display_name=request.display_name,
        )
        return ProviderCacheResponse(
            name=handle.name,
            model=handle.model,
            display_name=handle.display_name,
            expire_time=handle.expire_time,
            cached_tokens=handle.cached_tokens,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create provider context cache: {exc}")


@router.get("/api/v1/cache/provider", response_model=ProviderCacheListResponse, tags=["Phase 8: Cache & Provider Optimization"], summary="List active Gemini context caches")
async def list_provider_caches():
    """List all active server-side context caches in Gemini."""
    provider = _get_provider()
    try:
        handles = await provider.list_context_caches()
        items = [
            ProviderCacheResponse(
                name=h.name,
                model=h.model,
                display_name=h.display_name,
                expire_time=h.expire_time,
                cached_tokens=h.cached_tokens,
            )
            for h in handles
        ]
        return ProviderCacheListResponse(total=len(items), items=items)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list provider caches: {exc}")


@router.get("/api/v1/cache/provider/{cache_name:path}", response_model=ProviderCacheResponse, tags=["Phase 8: Cache & Provider Optimization"], summary="Get Gemini context cache details")
async def get_provider_cache(cache_name: str):
    """Fetch metadata for a specific Gemini context cache."""
    provider = _get_provider()
    handle = await provider.get_context_cache(cache_name=cache_name)
    if not handle:
        raise HTTPException(status_code=404, detail=f"Provider cache '{cache_name}' not found.")
    return ProviderCacheResponse(
        name=handle.name,
        model=handle.model,
        display_name=handle.display_name,
        expire_time=handle.expire_time,
        cached_tokens=handle.cached_tokens,
    )


@router.delete("/api/v1/cache/provider/{cache_name:path}", tags=["Phase 8: Cache & Provider Optimization"], summary="Delete Gemini context cache")
async def delete_provider_cache(cache_name: str):
    """Delete an active server-side context cache in Gemini."""
    provider = _get_provider()
    success = await provider.delete_context_cache(cache_name=cache_name)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to delete provider cache '{cache_name}'.")
    return {"status": "deleted", "cache_name": cache_name}


@router.get("/api/v1/cache/status", response_model=CacheHierarchyStatus, tags=["Phase 8: Cache & Provider Optimization"], summary="Get 3-Tier Multi-Level Cache Hierarchy status")
async def get_cache_hierarchy_status(db: AsyncSession = Depends(get_session)):
    """Return the 3-Tier Multi-Level Cache Hierarchy status breakdown."""
    provider = None
    try:
        provider = _get_provider()
    except Exception:
        pass

    status = await cache_service.get_hierarchy_status(db, provider=provider)
    return CacheHierarchyStatus(**status)


# ── Telemetry & Requests (Phase 9 Dashboard Backend) ─────────────────

@router.get("/api/v1/requests", response_model=RequestListResponse, tags=["Dashboard & Telemetry"], summary="List request logs with pagination and filters")
async def list_request_logs(
    limit: int = 50,
    offset: int = 0,
    model: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
):
    """List logged LLM requests with optional filtering by model or status."""
    total, items = await list_requests(db, limit=limit, offset=offset, model=model, status=status)
    log_items = [
        RequestLogItem(
            id=item.id,
            request_id=item.request_id,
            timestamp=item.timestamp,
            model=item.model,
            input_tokens=item.input_tokens,
            output_tokens=item.output_tokens,
            total_tokens=item.total_tokens,
            latency_ms=round(item.latency_ms, 2) if item.latency_ms is not None else None,
            status=item.status,
            error_message=item.error_message,
        )
        for item in items
    ]
    return RequestListResponse(total=total, items=log_items)


@router.get("/api/v1/metrics", response_model=DashboardMetricsResponse, tags=["Dashboard & Telemetry"], summary="Get gateway telemetry and cost metrics")
async def get_metrics(db: AsyncSession = Depends(get_session)):
    """Return aggregated telemetry, token savings, cost analytics, and charts data."""
    data = await get_dashboard_metrics(db)
    return DashboardMetricsResponse(**data)





