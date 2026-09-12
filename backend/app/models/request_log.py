"""SQLAlchemy models for request logging."""

from __future__ import annotations

import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared base for all ORM models."""
    pass


class RequestLog(Base):
    """Stores every LLM request that passes through the gateway."""

    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(64), unique=True, nullable=False, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    model = Column(String(64), nullable=False)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    latency_ms = Column(Float, nullable=True)
    status = Column(String(16), nullable=False, default="success")  # success | error
    error_message = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<RequestLog id={self.id} req={self.request_id} "
            f"model={self.model} status={self.status}>"
        )
