"""CCR (Compress - Cache - Retrieve) Service.

Manages storing raw context in SQLite, generating unique reference tokens,
and retrieving the original content on demand.
"""

from __future__ import annotations

import datetime
import json
import uuid
import logging
from typing import Any, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.context import ContextRecord
from app.services.content_router import ContentRouter
from app.services.compressors import get_compressor, JSONCompressor
from app.services.token_analyzer import estimate_tokens

logger = logging.getLogger(__name__)


class CCRService:
    """Core engine for Compress-Cache-Retrieve context lifecycle."""

    def __init__(self) -> None:
        self.router = ContentRouter()

    async def store_context(
        self,
        db: AsyncSession,
        *,
        content: str,
        content_type: Optional[str] = None,
        description: Optional[str] = None,
        options: Optional[dict[str, Any]] = None,
    ) -> ContextRecord:
        """Compress content, cache verbatim data into SQLite, and return ContextRecord."""
        raw_text = content.strip()
        original_size = len(content.encode("utf-8"))
        tokens_before = estimate_tokens(content)

        # 1. Determine Content Type
        if not content_type:
            detection = self.router.detect(raw_text)
            target_type = detection.content_type.value
        else:
            target_type = content_type.lower()

        # 2. Compress Content
        compressor = get_compressor(target_type)
        if not compressor and target_type == "json":
            compressor = JSONCompressor()

        comp_options = options or {}
        if compressor:
            comp_result = compressor.compress(raw_text, **comp_options)
            compressed_text = comp_result.compressed_content
            compressed_size = comp_result.compressed_size
            compression_ratio = comp_result.compression_ratio
            tokens_after = comp_result.estimated_tokens_after
            tokens_saved = comp_result.estimated_tokens_saved
            meta_dict = comp_result.metadata
        else:
            # Fallback compression (whitespace cleanup)
            compressed_text = " ".join(raw_text.split())
            compressed_size = len(compressed_text.encode("utf-8"))
            compression_ratio = round(compressed_size / max(1, original_size), 4)
            tokens_after = estimate_tokens(compressed_text)
            tokens_saved = max(0, tokens_before - tokens_after)
            meta_dict = {"strategy": "generic_whitespace_minification"}

        # 3. Generate unique context identifier
        context_id = f"ctx_{uuid.uuid4().hex[:12]}"
        now = datetime.datetime.now(datetime.timezone.utc)

        record = ContextRecord(
            context_id=context_id,
            content_type=target_type,
            original_content=raw_text,
            compressed_content=compressed_text,
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=compression_ratio,
            estimated_tokens_before=tokens_before,
            estimated_tokens_after=tokens_after,
            estimated_tokens_saved=tokens_saved,
            description=description,
            metadata_json=json.dumps(meta_dict) if meta_dict else None,
            access_count=0,
            created_at=now,
            accessed_at=now,
        )

        db.add(record)
        await db.commit()
        await db.refresh(record)

        logger.info(
            "CCR stored context_id=%s type=%s ratio=%.2f saved_tokens=%d",
            context_id,
            target_type,
            compression_ratio,
            tokens_saved,
        )
        return record

    async def get_context(
        self,
        db: AsyncSession,
        context_id: str,
    ) -> Optional[ContextRecord]:
        """Fetch context record metadata without retrieving the full original payload."""
        stmt = select(ContextRecord).where(ContextRecord.context_id == context_id)
        result = await db.execute(stmt)
        record = result.scalars().first()
        if record:
            record.access_count += 1
            record.accessed_at = datetime.datetime.now(datetime.timezone.utc)
            await db.commit()
            await db.refresh(record)
        return record

    async def retrieve_original(
        self,
        db: AsyncSession,
        context_id: str,
    ) -> Optional[ContextRecord]:
        """Fetch verbatim original content and increment access metrics."""
        return await self.get_context(db, context_id)

    async def list_contexts(
        self,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[int, list[ContextRecord]]:
        """Return total count and paginated list of context records."""
        count_stmt = select(func.count(ContextRecord.id))
        count_res = await db.execute(count_stmt)
        total = count_res.scalar_one()

        list_stmt = (
            select(ContextRecord)
            .order_by(ContextRecord.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        list_res = await db.execute(list_stmt)
        items = list(list_res.scalars().all())
        return total, items


# Singleton instance
ccr_service = CCRService()
