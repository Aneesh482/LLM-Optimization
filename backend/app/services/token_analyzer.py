"""Token analysis service.

Provides heuristic token estimation and context analysis.
We intentionally do NOT claim these are exact Gemini token counts —
they are practical estimates useful for optimization decisions.

Estimation method:
    estimated_tokens ≈ max(word_count * 1.3, char_count / 4)

This approximation is widely used and reasonable for English text.
For exact counts, Gemini's usage_metadata on actual API responses
is the authoritative source (handled in Phase 1).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MessageStats:
    """Analysis result for a single message."""
    index: int
    role: str
    content: str
    char_count: int
    word_count: int
    estimated_tokens: int


def estimate_tokens(text: str) -> int:
    """Estimate token count from text using a word/char heuristic.

    Returns a conservative estimate — never zero for non-empty text.
    """
    if not text:
        return 0

    words = len(text.split())
    chars = len(text)

    # Take the higher of two common heuristics
    by_words = int(words * 1.3)
    by_chars = int(chars / 4)

    return max(by_words, by_chars, 1)


def analyze_message(index: int, role: str, content: str) -> MessageStats:
    """Analyze a single message."""
    return MessageStats(
        index=index,
        role=role,
        content=content,
        char_count=len(content),
        word_count=len(content.split()),
        estimated_tokens=estimate_tokens(content),
    )


def analyze_messages(messages: list[dict]) -> dict:
    """Analyze a list of messages and return full statistics.

    Parameters
    ----------
    messages:
        Each dict must have ``role`` and ``content`` keys.

    Returns
    -------
    A dict matching the ``AnalyzeResponse`` schema.
    """

    # Per-message analysis
    stats: list[MessageStats] = [
        analyze_message(i, m["role"], m["content"])
        for i, m in enumerate(messages)
    ]

    token_counts = [s.estimated_tokens for s in stats]
    total_tokens = sum(token_counts)

    # ── Message-level breakdown ──────────────────────────────────────
    message_analyses = [
        {
            "index": s.index,
            "role": s.role,
            "char_count": s.char_count,
            "word_count": s.word_count,
            "estimated_tokens": s.estimated_tokens,
            "content_preview": s.content[:80],
        }
        for s in stats
    ]

    # ── Role distribution ────────────────────────────────────────────
    role_map: dict[str, dict] = {}
    for s in stats:
        if s.role not in role_map:
            role_map[s.role] = {"role": s.role, "count": 0, "total_estimated_tokens": 0}
        role_map[s.role]["count"] += 1
        role_map[s.role]["total_estimated_tokens"] += s.estimated_tokens

    # ── Largest sections (top 5) ─────────────────────────────────────
    sorted_stats = sorted(stats, key=lambda s: s.estimated_tokens, reverse=True)
    largest = [
        {
            "index": s.index,
            "role": s.role,
            "estimated_tokens": s.estimated_tokens,
            "percentage_of_total": round(
                (s.estimated_tokens / total_tokens * 100) if total_tokens > 0 else 0, 2
            ),
        }
        for s in sorted_stats[:5]
    ]

    # ── Assemble ─────────────────────────────────────────────────────
    return {
        "total_messages": len(messages),
        "total_characters": sum(s.char_count for s in stats),
        "total_words": sum(s.word_count for s in stats),
        "total_estimated_tokens": total_tokens,
        "messages": message_analyses,
        "role_distribution": list(role_map.values()),
        "largest_sections": largest,
        "avg_message_tokens": round(total_tokens / len(messages), 2) if messages else 0,
        "max_message_tokens": max(token_counts) if token_counts else 0,
        "min_message_tokens": min(token_counts) if token_counts else 0,
        "estimation_method": "heuristic",
    }
