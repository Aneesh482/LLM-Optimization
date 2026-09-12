"""Content Router — detects content type and routes to the right compressor.

Supported content types
-----------------------
- json         : valid JSON structures (objects, arrays)
- code         : source code (Python, JS, Java, C/C++, Go, Rust, SQL, etc.)
- logs         : timestamped or structured log lines
- conversation : chat / conversation history
- api_result   : tool / API / HTTP response payloads
- text         : plain text (fallback)

Detection is purely heuristic — no ML model, no external API call.
Each detector returns a confidence score between 0.0 and 1.0.
The router picks the type with the highest confidence, falling back to "text".
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum


# ── Content types ────────────────────────────────────────────────────

class ContentType(str, Enum):
    """All content types the gateway can route."""
    JSON = "json"
    CODE = "code"
    LOGS = "logs"
    CONVERSATION = "conversation"
    API_RESULT = "api_result"
    TEXT = "text"


# ── Detection result ────────────────────────────────────────────────

@dataclass
class DetectionResult:
    """Result from running all detectors on a piece of content."""
    content_type: ContentType
    confidence: float
    scores: dict[str, float]
    metadata: dict[str, object]


# ── Individual detectors ────────────────────────────────────────────
# Each returns a float in [0.0, 1.0].

def _detect_json(text: str) -> tuple[float, dict]:
    """Detect whether *text* is JSON or contains a significant JSON payload."""
    stripped = text.strip()
    if not stripped:
        return 0.0, {}

    parsed = None
    # 1. Direct JSON parse
    if stripped[0] in ("{", "["):
        try:
            parsed = json.loads(stripped)
        except (json.JSONDecodeError, ValueError):
            pass

    # 2. Embedded JSON / Fenced JSON
    if parsed is None:
        fence_match = re.search(r"```(?:json)?\s*([\[{].*?[\]}])\s*```", text, re.DOTALL)
        if fence_match:
            try:
                candidate = fence_match.group(1).strip()
                parsed = json.loads(candidate)
            except (json.JSONDecodeError, ValueError):
                pass

        if parsed is None:
            first_bracket = text.find("[")
            last_bracket = text.rfind("]")
            if first_bracket != -1 and last_bracket > first_bracket:
                candidate = text[first_bracket : last_bracket + 1]
                if len(candidate) > 40:
                    try:
                        p = json.loads(candidate)
                        if isinstance(p, list) and len(p) >= 2:
                            parsed = p
                    except (json.JSONDecodeError, ValueError):
                        pass

            if parsed is None:
                first_brace = text.find("{")
                last_brace = text.rfind("}")
                if first_brace != -1 and last_brace > first_brace:
                    candidate = text[first_brace : last_brace + 1]
                    if len(candidate) > 40:
                        try:
                            p = json.loads(candidate)
                            if isinstance(p, dict) and len(p) >= 2:
                                parsed = p
                        except (json.JSONDecodeError, ValueError):
                            pass

    if parsed is None:
        return 0.0, {}

    meta: dict[str, object] = {"valid_json": True}

    if isinstance(parsed, list):
        meta["json_type"] = "array"
        meta["array_length"] = len(parsed)
        confidence = 0.95 if len(parsed) > 5 else 0.85
    elif isinstance(parsed, dict):
        meta["json_type"] = "object"
        meta["key_count"] = len(parsed)
        confidence = 0.90 if len(parsed) > 3 else 0.80
    else:
        meta["json_type"] = "scalar"
        confidence = 0.5

    return confidence, meta


# Code detection ──────────────────────────────────────────────────────

# Patterns that strongly indicate programming-language source code.
_CODE_PATTERNS: list[tuple[re.Pattern, float]] = [
    # Python
    (re.compile(r"^\s*def\s+\w+\s*\(", re.MULTILINE), 0.35),
    (re.compile(r"^\s*class\s+\w+[\s(:]", re.MULTILINE), 0.30),
    (re.compile(r"^\s*import\s+\w+", re.MULTILINE), 0.25),
    (re.compile(r"^\s*from\s+\w+\s+import", re.MULTILINE), 0.25),
    (re.compile(r"if\s+__name__\s*==\s*['\"]__main__['\"]", re.MULTILINE), 0.30),

    # JavaScript / TypeScript
    (re.compile(r"\b(const|let|var)\s+\w+\s*=", re.MULTILINE), 0.20),
    (re.compile(r"\bfunction\s+\w+\s*\(", re.MULTILINE), 0.30),
    (re.compile(r"=>\s*\{", re.MULTILINE), 0.15),
    (re.compile(r"\bexport\s+(default\s+)?(function|class|const)", re.MULTILINE), 0.30),

    # Java / C# / C++ / Go / Rust
    (re.compile(r"^\s*public\s+(static\s+)?[\w<>\[\]]+\s+\w+\s*\(", re.MULTILINE), 0.35),
    (re.compile(r"^\s*(func|fn)\s+\w+\s*\(", re.MULTILINE), 0.30),
    (re.compile(r"#include\s*<\w+", re.MULTILINE), 0.35),

    # SQL
    (re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|CREATE TABLE|ALTER TABLE)\b", re.IGNORECASE), 0.25),

    # General code indicators
    (re.compile(r"[{};]\s*$", re.MULTILINE), 0.10),
    (re.compile(r"^\s*//\s+", re.MULTILINE), 0.10),
    (re.compile(r"^\s*#\s+(?!#+\s)", re.MULTILINE), 0.05),  # comment, not markdown heading
]


def _detect_code(text: str) -> tuple[float, dict]:
    """Detect whether *text* is source code."""
    if not text.strip():
        return 0.0, {}

    total = 0.0
    matched: list[str] = []

    for pattern, weight in _CODE_PATTERNS:
        if pattern.search(text):
            total += weight
            matched.append(pattern.pattern[:40])

    # Extra boost: if many lines end with braces / semicolons
    lines = text.splitlines()
    if lines:
        code_line_ratio = sum(
            1 for ln in lines if re.search(r"[{};:]\s*$", ln)
        ) / len(lines)
        total += code_line_ratio * 0.15

    confidence = min(total, 1.0)
    meta = {"matched_patterns": len(matched), "sample_matches": matched[:5]}
    return confidence, meta


# Log detection ───────────────────────────────────────────────────────

_LOG_PATTERNS: list[tuple[re.Pattern, float]] = [
    # ISO timestamps at start of line
    (re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}", re.MULTILINE), 0.35),
    # Common log levels
    (re.compile(r"\b(DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL|CRITICAL)\b", re.MULTILINE), 0.30),
    # Syslog-style: "Mon DD HH:MM:SS"
    (re.compile(r"^[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}", re.MULTILINE), 0.30),
    # Bracketed timestamps "[2024-01-01 12:00:00]"
    (re.compile(r"^\[\d{4}-\d{2}-\d{2}", re.MULTILINE), 0.30),
    # Common log prefixes
    (re.compile(r"^\d{2}:\d{2}:\d{2}\.\d+", re.MULTILINE), 0.20),
    # Stack-trace patterns
    (re.compile(r"Traceback \(most recent call last\)", re.MULTILINE), 0.25),
    (re.compile(r"^\s+at\s+\w+[\w.]*\([\w.]+:\d+\)", re.MULTILINE), 0.20),
]


def _detect_logs(text: str) -> tuple[float, dict]:
    """Detect whether *text* looks like application logs."""
    if not text.strip():
        return 0.0, {}

    total = 0.0
    matched: list[str] = []

    for pattern, weight in _LOG_PATTERNS:
        hits = len(pattern.findall(text))
        if hits > 0:
            matched.append(pattern.pattern[:40])
            # More hits → stronger signal (capped)
            total += weight * min(hits / 3, 1.5)

    # Extra: many lines with similar structure → logs tend to be repetitive
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) > 5:
        # Check if most lines start with a timestamp-like pattern
        ts_re = re.compile(r"^[\[\d]")
        ts_ratio = sum(1 for ln in lines if ts_re.match(ln)) / len(lines)
        total += ts_ratio * 0.15

    confidence = min(total, 1.0)
    meta = {"matched_patterns": len(matched), "line_count": len(lines)}
    return confidence, meta


# Conversation detection ──────────────────────────────────────────────

_CONVERSATION_PATTERNS: list[tuple[re.Pattern, float]] = [
    # "User:", "Assistant:", "Human:", "AI:", etc.
    (re.compile(r"^(User|Human|Assistant|AI|Bot|System)\s*:", re.MULTILINE | re.IGNORECASE), 0.35),
    # Messages with role markers
    (re.compile(r'["\']role["\']\s*:\s*["\'](user|assistant|system)', re.IGNORECASE), 0.30),
    # Multi-turn question/answer
    (re.compile(r"^Q:\s+.+\nA:\s+", re.MULTILINE), 0.30),
    # Dialogue markers
    (re.compile(r"^>\s+.+", re.MULTILINE), 0.10),
]


def _detect_conversation(text: str) -> tuple[float, dict]:
    """Detect whether *text* is a conversation transcript."""
    if not text.strip():
        return 0.0, {}

    total = 0.0
    matched: list[str] = []

    for pattern, weight in _CONVERSATION_PATTERNS:
        hits = len(pattern.findall(text))
        if hits > 0:
            matched.append(pattern.pattern[:40])
            total += weight * min(hits / 2, 1.5)

    confidence = min(total, 1.0)
    meta = {"matched_patterns": len(matched)}
    return confidence, meta


# API / tool result detection ─────────────────────────────────────────

_API_RESULT_PATTERNS: list[tuple[re.Pattern, float]] = [
    # Common API response keys
    (re.compile(r'"(status|statusCode|status_code)"\s*:', re.IGNORECASE), 0.20),
    (re.compile(r'"(data|results?|items|records|response|payload)"\s*:', re.IGNORECASE), 0.20),
    (re.compile(r'"(error|message|code)"\s*:', re.IGNORECASE), 0.10),
    # HTTP methods / status codes
    (re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+/[\w/]+", re.MULTILINE), 0.25),
    (re.compile(r"\bHTTP/\d\.\d\s+\d{3}\b"), 0.25),
    # URL patterns
    (re.compile(r"https?://[\w./-]+/api/", re.IGNORECASE), 0.15),
    # Pagination keys
    (re.compile(r'"(page|per_page|total|next_cursor|offset|limit)"\s*:', re.IGNORECASE), 0.15),
]


def _detect_api_result(text: str) -> tuple[float, dict]:
    """Detect whether *text* looks like a tool / API response payload."""
    if not text.strip():
        return 0.0, {}

    # Must look structurally like JSON for this to be a strong signal.
    has_json = text.strip().startswith(("{", "["))

    total = 0.0
    matched: list[str] = []

    for pattern, weight in _API_RESULT_PATTERNS:
        if pattern.search(text):
            matched.append(pattern.pattern[:40])
            # Boost if the text is also JSON
            total += weight * (1.3 if has_json else 0.8)

    confidence = min(total, 1.0)
    meta = {"matched_patterns": len(matched), "appears_json": has_json}
    return confidence, meta


# ── Content Router ───────────────────────────────────────────────────

class ContentRouter:
    """Classifies arbitrary text content and routes it to a type.

    Usage::

        router = ContentRouter()
        result = router.detect(some_text)
        # result.content_type -> ContentType.CODE
        # result.confidence   -> 0.85
    """

    # Ordered list of (detector_fn, content_type).
    # The router runs *all* of them and picks the highest confidence.
    _detectors: list[tuple] = [
        (_detect_json, ContentType.JSON),
        (_detect_code, ContentType.CODE),
        (_detect_logs, ContentType.LOGS),
        (_detect_conversation, ContentType.CONVERSATION),
        (_detect_api_result, ContentType.API_RESULT),
    ]

    # Minimum confidence a detector must reach to beat the TEXT fallback.
    MIN_CONFIDENCE = 0.20

    def detect(self, content: str) -> DetectionResult:
        """Run all detectors and return the best match.

        If no detector exceeds ``MIN_CONFIDENCE``, the content is
        classified as plain **text** with confidence 1.0.
        """
        scores: dict[str, float] = {}
        all_meta: dict[str, object] = {}
        best_type = ContentType.TEXT
        best_conf = 0.0

        for detector_fn, ctype in self._detectors:
            conf, meta = detector_fn(content)
            scores[ctype.value] = round(conf, 4)
            if meta:
                all_meta[ctype.value] = meta

            if conf > best_conf:
                best_conf = conf
                best_type = ctype

        # TEXT fallback
        scores[ContentType.TEXT.value] = round(1.0 - best_conf, 4) if best_conf > 0 else 1.0

        if best_conf < self.MIN_CONFIDENCE:
            best_type = ContentType.TEXT
            best_conf = 1.0

        return DetectionResult(
            content_type=best_type,
            confidence=round(best_conf, 4),
            scores=scores,
            metadata=all_meta,
        )

    def detect_messages(self, messages: list[dict]) -> list[dict]:
        """Analyse each message in a conversation and return per-message routing.

        Parameters
        ----------
        messages:
            List of ``{"role": ..., "content": ...}`` dicts.

        Returns
        -------
        One dict per message with ``index``, ``role``, ``content_type``,
        ``confidence``, and ``scores``.
        """
        results: list[dict] = []
        for idx, msg in enumerate(messages):
            det = self.detect(msg.get("content", ""))
            results.append(
                {
                    "index": idx,
                    "role": msg.get("role", "unknown"),
                    "content_type": det.content_type.value,
                    "confidence": det.confidence,
                    "scores": det.scores,
                    "content_preview": msg.get("content", "")[:80],
                }
            )
        return results

    def route_summary(self, messages: list[dict]) -> dict:
        """High-level summary: how many messages map to each content type.

        Returns a dict suitable for the ``RouteResponse`` schema.
        """
        per_message = self.detect_messages(messages)

        # Aggregate
        type_counts: dict[str, int] = {}
        for pm in per_message:
            ct = pm["content_type"]
            type_counts[ct] = type_counts.get(ct, 0) + 1

        return {
            "total_messages": len(messages),
            "type_distribution": [
                {"content_type": ct, "count": cnt}
                for ct, cnt in sorted(type_counts.items(), key=lambda x: -x[1])
            ],
            "messages": per_message,
        }
