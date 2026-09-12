"""Unit tests for LogCompressor (pattern deduplication and error preservation)."""

from __future__ import annotations

import pytest
from app.services.compressors.log_compressor import LogCompressor


@pytest.fixture
def compressor() -> LogCompressor:
    return LogCompressor()


def test_compress_empty_logs(compressor: LogCompressor):
    res = compressor.compress("")
    assert res.compressed_content == ""
    assert res.content_type == "logs"


def test_compress_repetitive_info_logs(compressor: LogCompressor):
    log_lines = []
    # 40 repeated health check lines
    for i in range(40):
        log_lines.append(f"2026-09-09T12:00:{i:02d} INFO 192.168.1.10 GET /api/v1/health status=200 latency=1.{i}ms")

    # 1 Error line in the middle
    log_lines.append("2026-09-09T12:00:45 ERROR 192.168.1.55 Database connection timeout on pool-3")
    log_lines.append("Traceback (most recent call last):\n  File 'server.py', line 99, in connect\n    raise ConnectionError('Failed')")

    raw_logs = "\n".join(log_lines)
    res = compressor.compress(raw_logs, repeat_threshold=3)

    assert res.content_type == "logs"
    assert res.compression_ratio < 0.6
    assert res.estimated_tokens_saved > 0

    compressed = res.compressed_content
    # Group header should collapse repeated health checks
    assert "[Repeated" in compressed
    # Error and traceback must be preserved intact
    assert "ERROR 192.168.1.55 Database connection timeout on pool-3" in compressed
    assert "raise ConnectionError('Failed')" in compressed


def test_compress_under_threshold(compressor: LogCompressor):
    short_log = "2026-09-09 INFO User logged in\n2026-09-09 INFO User logged out"
    res = compressor.compress(short_log, min_lines=10)
    assert res.compressed_content == short_log
    assert res.compression_ratio == 1.0
