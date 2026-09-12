"""SQLAlchemy model for CCR (Compress - Cache - Retrieve) storage."""

from __future__ import annotations

import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from app.models.request_log import Base


class ContextRecord(Base):
    """Stores original large content in SQLite with compression metadata and retrieval key."""

    __tablename__ = "context_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    context_id = Column(String(64), unique=True, nullable=False, index=True)
    content_type = Column(String(32), nullable=False, default="json")
    
    # Verbatim content vs compressed content
    original_content = Column(Text, nullable=False)
    compressed_content = Column(Text, nullable=False)
    
    # Byte size and compression metrics
    original_size = Column(Integer, nullable=False)
    compressed_size = Column(Integer, nullable=False)
    compression_ratio = Column(Float, nullable=False)
    
    # Heuristic token metrics
    estimated_tokens_before = Column(Integer, nullable=False, default=0)
    estimated_tokens_after = Column(Integer, nullable=False, default=0)
    estimated_tokens_saved = Column(Integer, nullable=False, default=0)
    
    # Metadata & description
    description = Column(String(255), nullable=True)
    metadata_json = Column(Text, nullable=True)  # JSON-encoded metadata
    
    # Access and lifecycle tracking
    access_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    accessed_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<ContextRecord id={self.id} context_id={self.context_id} "
            f"type={self.content_type} ratio={self.compression_ratio}>"
        )
