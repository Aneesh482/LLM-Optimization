"""Log Compressor for LLM Context Optimization.

Features
--------
1. Pattern Template Masking: Normalizes dynamic tokens (IPs, UUIDs, numbers, timestamps, hashes).
2. Repetitive Log Deduplication & Grouping:
   - Groups continuous and batch repeated logs by signature.
   - Summarizes high-volume repeated events:
     e.g., "[Repeated 450x from 10:14:00 to 10:18:30]: GET /api/v1/health 200 OK"
3. Full Error & Traceback Preservation:
   - Preserves all ERROR, CRITICAL, FATAL, and WARN logs with exact timestamps and stack traces.
4. Anomaly Detection:
   - Preserves rare or unique log messages that deviate from background traffic.
5. Log Level Distribution & Metrics:
   - Reports counts of INFO, WARN, ERROR, DEBUG, byte savings, and token reductions.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Optional

from app.services.compressors.base import BaseCompressor, CompressionResult
from app.services.token_analyzer import estimate_tokens


class LogCompressor(BaseCompressor):
    """Pattern-aware log stream compressor."""

    DEFAULT_MIN_LINES_TO_COMPRESS = 10
    DEFAULT_REPEAT_THRESHOLD = 3

    _IPV4_RE = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
    _UUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
    _HEX_RE = re.compile(r"\b0x[0-9a-fA-F]+\b|\b[0-9a-fA-F]{16,64}\b")
    _NUM_RE = re.compile(r"\b\d+(?:\.\d+)?(?:ms|s|us|ns|kb|mb|gb|b|%|hz)?\b|\b\d+\b", re.IGNORECASE)
    _TIMESTAMP_RE = re.compile(r"\d{4}[-/]\d{2}[-/]\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?")
    _LOG_LEVEL_RE = re.compile(r"\b(DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL|FATAL|EXCEPTION)\b", re.IGNORECASE)

    def content_type(self) -> str:
        return "logs"

    def compress(
        self,
        content: str,
        *,
        min_lines: Optional[int] = None,
        repeat_threshold: Optional[int] = None,
        preserve_all_errors: bool = True,
        **options: Any,
    ) -> CompressionResult:
        """Compress log stream by collapsing repeated templates while preserving errors and outliers."""
        raw_text = content.strip()
        original_size = len(content.encode("utf-8"))
        tokens_before = estimate_tokens(content)

        if not raw_text:
            return self._build_result(
                original=content,
                compressed="",
                original_size=original_size,
                metadata={"strategy": "empty"},
            )

        lines = raw_text.splitlines()
        threshold = min_lines or self.DEFAULT_MIN_LINES_TO_COMPRESS
        min_repeats = repeat_threshold or self.DEFAULT_REPEAT_THRESHOLD

        if len(lines) < threshold:
            # Under threshold: return verbatim
            return self._build_result(
                original=content,
                compressed=raw_text,
                original_size=original_size,
                metadata={
                    "strategy": "verbatim_under_threshold",
                    "original_lines": len(lines),
                },
            )

        # 1. Parse and classify log lines
        parsed_entries = []
        level_counts: Counter[str] = Counter()
        for idx, line in enumerate(lines):
            level_match = self._LOG_LEVEL_RE.search(line)
            level = level_match.group(1).upper() if level_match else "UNKNOWN"
            level_counts[level] += 1

            ts_match = self._TIMESTAMP_RE.search(line)
            timestamp = ts_match.group(0) if ts_match else None

            template = self._create_template(line)
            is_error = level in ("ERROR", "CRITICAL", "FATAL", "EXCEPTION", "WARN", "WARNING") or "exception" in line.lower()

            parsed_entries.append({
                "index": idx,
                "raw": line,
                "level": level,
                "timestamp": timestamp,
                "template": template,
                "is_error": is_error,
            })

        # 2. Sequential Grouping of repeated non-error templates
        output_lines: list[str] = []
        errors_preserved = 0
        groups_collapsed = 0

        i = 0
        n = len(parsed_entries)
        while i < n:
            entry = parsed_entries[i]

            # If it's an error/warning or stacktrace, preserve verbatim
            if entry["is_error"] and preserve_all_errors:
                output_lines.append(entry["raw"])
                errors_preserved += 1
                i += 1
                continue

            # Look ahead to count consecutive identical templates
            j = i + 1
            while j < n and not parsed_entries[j]["is_error"] and parsed_entries[j]["template"] == entry["template"]:
                j += 1

            count = j - i
            if count >= min_repeats:
                first_ts = entry["timestamp"] or f"line {i+1}"
                last_ts = parsed_entries[j - 1]["timestamp"] or f"line {j}"
                rep_header = f"[Repeated {count}x from {first_ts} to {last_ts}]: {entry['raw']}"
                output_lines.append(rep_header)
                groups_collapsed += 1
            else:
                for k in range(i, j):
                    output_lines.append(parsed_entries[k]["raw"])

            i = j

        # 3. Add Summary Header if significant compression occurred
        summary_header = (
            f"[Log Summary: {len(lines)} original lines -> {len(output_lines)} compressed lines | "
            f"Levels: {dict(level_counts.most_common())} | "
            f"Errors Preserved: {errors_preserved}]\n"
        )
        compressed_text = summary_header + "\n".join(output_lines)
        compressed_bytes = len(compressed_text.encode("utf-8"))

        # If compression made it slightly larger due to header on small inputs, return verbatim
        if compressed_bytes >= original_size:
            return self._build_result(
                original=content,
                compressed=raw_text,
                original_size=original_size,
                metadata={"strategy": "verbatim_fallback"},
            )

        meta = {
            "strategy": "template_deduplication_and_error_preservation",
            "original_lines": len(lines),
            "compressed_lines": len(output_lines),
            "groups_collapsed": groups_collapsed,
            "errors_preserved": errors_preserved,
            "level_distribution": dict(level_counts),
        }

        return self._build_result(
            original=content,
            compressed=compressed_text,
            original_size=original_size,
            metadata=meta,
        )

    # ── Helpers ────────────────────────────────────────────────────────

    def _create_template(self, line: str) -> str:
        """Replace dynamic variables with generic placeholder masks."""
        tmpl = self._TIMESTAMP_RE.sub("<TS>", line)
        tmpl = self._IPV4_RE.sub("<IP>", tmpl)
        tmpl = self._UUID_RE.sub("<UUID>", tmpl)
        tmpl = self._HEX_RE.sub("<HEX>", tmpl)
        tmpl = self._NUM_RE.sub("<NUM>", tmpl)
        return tmpl.strip()

    @staticmethod
    def _build_result(
        original: str,
        compressed: str,
        original_size: int,
        metadata: dict[str, Any],
    ) -> CompressionResult:
        compressed_bytes = len(compressed.encode("utf-8"))
        tokens_before = estimate_tokens(original)
        tokens_after = estimate_tokens(compressed)
        ratio = round(compressed_bytes / max(1, original_size), 4)

        return CompressionResult(
            original_content=original,
            compressed_content=compressed,
            original_size=original_size,
            compressed_size=compressed_bytes,
            compression_ratio=ratio,
            estimated_tokens_before=tokens_before,
            estimated_tokens_after=tokens_after,
            estimated_tokens_saved=max(0, tokens_before - tokens_after),
            content_type="logs",
            metadata=metadata,
        )
