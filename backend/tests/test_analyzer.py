"""Tests for the token_analyzer service."""

import pytest

from app.services.token_analyzer import estimate_tokens, analyze_message, analyze_messages


class TestEstimateTokens:
    """Verify token estimation heuristic."""

    def test_empty_string_returns_zero(self):
        assert estimate_tokens("") == 0

    def test_single_word(self):
        result = estimate_tokens("hello")
        assert result >= 1

    def test_short_sentence(self):
        result = estimate_tokens("The quick brown fox jumps over the lazy dog")
        # 9 words → ~12 tokens by word heuristic, 44 chars → 11 by char heuristic
        assert 10 <= result <= 20

    def test_long_text_scales(self):
        short = estimate_tokens("hello world")
        long = estimate_tokens("hello world " * 100)
        assert long > short * 50  # should scale roughly linearly

    def test_never_returns_zero_for_nonempty(self):
        assert estimate_tokens("x") >= 1
        assert estimate_tokens("  ") >= 1


class TestAnalyzeMessage:
    """Verify single-message analysis."""

    def test_basic_message(self):
        result = analyze_message(0, "user", "Hello, how are you?")
        assert result.index == 0
        assert result.role == "user"
        assert result.char_count == 19
        assert result.word_count == 4
        assert result.estimated_tokens >= 1

    def test_empty_content(self):
        result = analyze_message(0, "user", "")
        assert result.char_count == 0
        assert result.word_count == 0
        assert result.estimated_tokens == 0


class TestAnalyzeMessages:
    """Verify full message-list analysis."""

    def test_single_message(self):
        messages = [{"role": "user", "content": "Explain recursion."}]
        result = analyze_messages(messages)

        assert result["total_messages"] == 1
        assert result["total_characters"] == 18
        assert result["total_words"] == 2
        assert result["total_estimated_tokens"] >= 1
        assert len(result["messages"]) == 1
        assert result["estimation_method"] == "heuristic"

    def test_multi_message_conversation(self):
        messages = [
            {"role": "system", "content": "You are a Python tutor."},
            {"role": "user", "content": "What is a decorator?"},
            {"role": "assistant", "content": "A decorator is a function that wraps another function."},
            {"role": "user", "content": "Show me an example."},
        ]
        result = analyze_messages(messages)

        assert result["total_messages"] == 4
        assert len(result["messages"]) == 4
        assert result["avg_message_tokens"] > 0
        assert result["max_message_tokens"] >= result["min_message_tokens"]

    def test_role_distribution(self):
        messages = [
            {"role": "system", "content": "Be brief."},
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
            {"role": "user", "content": "Bye"},
        ]
        result = analyze_messages(messages)
        roles = {r["role"]: r for r in result["role_distribution"]}

        assert roles["system"]["count"] == 1
        assert roles["user"]["count"] == 2
        assert roles["assistant"]["count"] == 1

    def test_largest_sections_sorted(self):
        messages = [
            {"role": "user", "content": "short"},
            {"role": "user", "content": "a " * 500},  # large
            {"role": "user", "content": "medium length message here"},
        ]
        result = analyze_messages(messages)
        largest = result["largest_sections"]

        # Should be sorted descending by token count
        for i in range(len(largest) - 1):
            assert largest[i]["estimated_tokens"] >= largest[i + 1]["estimated_tokens"]

        # The large message should be first
        assert largest[0]["index"] == 1

    def test_largest_sections_capped_at_five(self):
        messages = [{"role": "user", "content": f"Message {i}"} for i in range(10)]
        result = analyze_messages(messages)
        assert len(result["largest_sections"]) <= 5

    def test_percentage_of_total_sums_reasonably(self):
        messages = [
            {"role": "user", "content": "Hello world"},
            {"role": "assistant", "content": "Hi there, how can I help?"},
        ]
        result = analyze_messages(messages)
        total_pct = sum(s["percentage_of_total"] for s in result["largest_sections"])
        # With only 2 messages, both should appear and sum to 100
        assert 99.0 <= total_pct <= 101.0

    def test_content_preview_truncated(self):
        long_msg = "x" * 200
        messages = [{"role": "user", "content": long_msg}]
        result = analyze_messages(messages)
        assert len(result["messages"][0]["content_preview"]) == 80
