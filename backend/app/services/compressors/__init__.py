"""Compressor modules and factory."""

from __future__ import annotations

from typing import Optional
from app.services.compressors.base import BaseCompressor, CompressionResult
from app.services.compressors.json_compressor import JSONCompressor
from app.services.compressors.code_compressor import CodeCompressor
from app.services.compressors.log_compressor import LogCompressor

# Registry of available compressors
_COMPRESSORS: dict[str, BaseCompressor] = {
    "json": JSONCompressor(),
    "code": CodeCompressor(),
    "logs": LogCompressor(),
    "log": LogCompressor(),
}


def get_compressor(content_type: str) -> Optional[BaseCompressor]:
    """Return the compressor instance for the given content type, or None."""
    return _COMPRESSORS.get(content_type.lower())


__all__ = [
    "BaseCompressor",
    "CompressionResult",
    "JSONCompressor",
    "CodeCompressor",
    "LogCompressor",
    "get_compressor",
]
