"""Base compressor interface.

Every content-type compressor (JSON, code, logs, text, etc.) implements
this interface so the content router can treat them interchangeably.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class CompressionResult:
    """Outcome of compressing a single piece of content.

    Attributes
    ----------
    original_content : str
        The verbatim input.
    compressed_content : str
        The compressed representation (still valid text / JSON).
    original_size : int
        Byte length of the original.
    compressed_size : int
        Byte length of the compressed output.
    compression_ratio : float
        ``compressed_size / original_size`` — lower is better.
    estimated_tokens_before : int
        Heuristic token count of the original.
    estimated_tokens_after : int
        Heuristic token count of the compressed output.
    estimated_tokens_saved : int
        ``tokens_before - tokens_after``.
    content_type : str
        What kind of content was compressed (e.g. "json").
    metadata : dict
        Extra information specific to the compressor.
    """

    original_content: str
    compressed_content: str
    original_size: int
    compressed_size: int
    compression_ratio: float
    estimated_tokens_before: int
    estimated_tokens_after: int
    estimated_tokens_saved: int
    content_type: str
    metadata: dict = field(default_factory=dict)


class BaseCompressor(abc.ABC):
    """Interface every compressor must implement."""

    @abc.abstractmethod
    def compress(self, content: str, **options: Any) -> CompressionResult:
        """Compress *content* and return a ``CompressionResult``."""
        ...

    @abc.abstractmethod
    def content_type(self) -> str:
        """The content type this compressor handles, e.g. ``"json"``."""
        ...
