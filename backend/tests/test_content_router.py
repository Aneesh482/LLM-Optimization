"""Tests for the content router — detection logic and API endpoints."""

from __future__ import annotations

import json
import textwrap

import pytest

from app.services.content_router import ContentRouter, ContentType


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def router():
    return ContentRouter()


# ── Sample payloads ──────────────────────────────────────────────────

SAMPLE_JSON = json.dumps(
    {
        "users": [
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "email": "bob@example.com"},
            {"id": 3, "name": "Charlie", "email": "charlie@example.com"},
            {"id": 4, "name": "Diana", "email": "diana@example.com"},
            {"id": 5, "name": "Eve", "email": "eve@example.com"},
            {"id": 6, "name": "Frank", "email": "frank@example.com"},
        ]
    },
    indent=2,
)

SAMPLE_JSON_ARRAY = json.dumps(
    [{"status": 200, "data": i} for i in range(10)],
    indent=2,
)

SAMPLE_PYTHON = textwrap.dedent("""\
    import os
    from pathlib import Path

    class FileProcessor:
        \"\"\"Process files in a directory.\"\"\"

        def __init__(self, root: Path):
            self.root = root

        def process(self) -> list[str]:
            results = []
            for f in self.root.iterdir():
                if f.is_file():
                    results.append(f.name)
            return results

    if __name__ == "__main__":
        fp = FileProcessor(Path("."))
        print(fp.process())
""")

SAMPLE_JAVASCRIPT = textwrap.dedent("""\
    const express = require('express');
    const app = express();

    function handleRequest(req, res) {
        const { id } = req.params;
        res.json({ message: `Hello ${id}` });
    }

    app.get('/api/users/:id', handleRequest);

    export default app;
""")

SAMPLE_LOGS = textwrap.dedent("""\
    2024-06-15T10:23:01.456Z INFO  [main] Server started on port 8080
    2024-06-15T10:23:01.789Z DEBUG [db] Connection pool initialized (size=10)
    2024-06-15T10:23:05.123Z INFO  [api] GET /health 200 12ms
    2024-06-15T10:23:06.456Z WARN  [auth] Token expiring in 5 minutes for user=42
    2024-06-15T10:23:07.789Z ERROR [api] POST /users 500 Internal Server Error
    2024-06-15T10:23:07.790Z ERROR [api] Traceback (most recent call last):
    2024-06-15T10:23:08.001Z INFO  [api] GET /health 200 8ms
    2024-06-15T10:23:09.234Z INFO  [api] GET /users 200 45ms
""")

SAMPLE_CONVERSATION = textwrap.dedent("""\
    User: How do I reverse a linked list?
    Assistant: You can reverse a linked list iteratively by maintaining three pointers:
    previous, current, and next. Here's how:
    1. Initialize previous to None
    2. Iterate through the list
    3. At each step, save current.next, set current.next = previous, then advance.

    User: Can you show me the code?
    Assistant: Sure! Here's a Python implementation:
    ```python
    def reverse(head):
        prev = None
        current = head
        while current:
            nxt = current.next
            current.next = prev
            prev = current
            current = nxt
        return prev
    ```

    User: Thanks! What's the time complexity?
    Assistant: The time complexity is O(n) where n is the number of nodes.
""")

SAMPLE_API_RESULT = json.dumps(
    {
        "status": 200,
        "statusCode": 200,
        "data": {
            "results": [
                {"id": 1, "title": "First post"},
                {"id": 2, "title": "Second post"},
            ],
            "total": 42,
            "page": 1,
            "per_page": 10,
            "next_cursor": "abc123",
        },
    },
    indent=2,
)

SAMPLE_PLAIN_TEXT = textwrap.dedent("""\
    The quick brown fox jumped over the lazy dog. This is just a regular
    paragraph of plain English text with no special structure. It doesn't
    contain code, logs, JSON, or any particular technical format. It's the
    kind of text you might find in an essay, an email, or a readme file
    that has no markdown formatting or structured data.
""")


# ═════════════════════════════════════════════════════════════════════
# Unit tests — detection logic
# ═════════════════════════════════════════════════════════════════════

class TestJsonDetection:
    def test_detects_json_object(self, router: ContentRouter):
        result = router.detect(SAMPLE_JSON)
        assert result.content_type == ContentType.JSON
        assert result.confidence >= 0.8

    def test_detects_json_array(self, router: ContentRouter):
        result = router.detect(SAMPLE_JSON_ARRAY)
        assert result.content_type == ContentType.JSON
        assert result.confidence >= 0.8

    def test_json_metadata(self, router: ContentRouter):
        result = router.detect(SAMPLE_JSON)
        meta = result.metadata.get("json", {})
        assert meta.get("valid_json") is True

    def test_invalid_json_not_detected(self, router: ContentRouter):
        result = router.detect("{this is not valid json at all}")
        assert result.content_type != ContentType.JSON

    def test_plain_number_low_confidence(self, router: ContentRouter):
        result = router.detect("42")
        # A bare number is technically valid JSON but shouldn't beat text.
        assert result.content_type == ContentType.TEXT


class TestCodeDetection:
    def test_detects_python(self, router: ContentRouter):
        result = router.detect(SAMPLE_PYTHON)
        assert result.content_type == ContentType.CODE
        assert result.confidence >= 0.5

    def test_detects_javascript(self, router: ContentRouter):
        result = router.detect(SAMPLE_JAVASCRIPT)
        assert result.content_type == ContentType.CODE
        assert result.confidence >= 0.4

    def test_short_snippet(self, router: ContentRouter):
        result = router.detect("def foo():\n    return 42\n")
        assert result.content_type == ContentType.CODE


class TestLogDetection:
    def test_detects_logs(self, router: ContentRouter):
        result = router.detect(SAMPLE_LOGS)
        assert result.content_type == ContentType.LOGS
        assert result.confidence >= 0.5

    def test_single_log_line_lower_confidence(self, router: ContentRouter):
        result = router.detect("2024-06-15T10:23:01.456Z INFO Server started")
        # One line might match but shouldn't be super high confidence
        assert result.scores.get("logs", 0) > 0


class TestConversationDetection:
    def test_detects_conversation(self, router: ContentRouter):
        result = router.detect(SAMPLE_CONVERSATION)
        assert result.content_type == ContentType.CONVERSATION
        assert result.confidence >= 0.4

    def test_qa_format(self, router: ContentRouter):
        text = "Q: What is Python?\nA: A programming language.\nQ: Is it fast?\nA: Reasonably."
        result = router.detect(text)
        assert result.content_type == ContentType.CONVERSATION


class TestApiResultDetection:
    def test_detects_api_result(self, router: ContentRouter):
        result = router.detect(SAMPLE_API_RESULT)
        # API result has both JSON and API signals; depending on scoring
        # it might classify as JSON or api_result — both are reasonable.
        assert result.content_type in (ContentType.JSON, ContentType.API_RESULT)
        assert result.confidence >= 0.5

    def test_http_response(self, router: ContentRouter):
        text = 'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{"data": []}'
        result = router.detect(text)
        assert result.scores.get("api_result", 0) > 0


class TestTextFallback:
    def test_plain_text_detected(self, router: ContentRouter):
        result = router.detect(SAMPLE_PLAIN_TEXT)
        assert result.content_type == ContentType.TEXT
        assert result.confidence >= 0.5

    def test_empty_string(self, router: ContentRouter):
        result = router.detect("")
        assert result.content_type == ContentType.TEXT

    def test_whitespace_only(self, router: ContentRouter):
        result = router.detect("   \n\n   ")
        assert result.content_type == ContentType.TEXT


# ═════════════════════════════════════════════════════════════════════
# Batch detection
# ═════════════════════════════════════════════════════════════════════

class TestBatchDetection:
    def test_detect_messages(self, router: ContentRouter):
        messages = [
            {"role": "user", "content": SAMPLE_JSON},
            {"role": "user", "content": SAMPLE_PYTHON},
            {"role": "user", "content": SAMPLE_PLAIN_TEXT},
        ]
        results = router.detect_messages(messages)
        assert len(results) == 3
        assert results[0]["content_type"] == "json"
        assert results[1]["content_type"] == "code"
        assert results[2]["content_type"] == "text"

    def test_route_summary(self, router: ContentRouter):
        messages = [
            {"role": "user", "content": SAMPLE_JSON},
            {"role": "user", "content": SAMPLE_PYTHON},
            {"role": "user", "content": SAMPLE_PLAIN_TEXT},
        ]
        summary = router.route_summary(messages)
        assert summary["total_messages"] == 3
        assert len(summary["type_distribution"]) >= 2
        assert len(summary["messages"]) == 3


# ═════════════════════════════════════════════════════════════════════
# API endpoint tests
# ═════════════════════════════════════════════════════════════════════

class TestRouteEndpoint:
    @pytest.mark.asyncio
    async def test_route_batch(self, client):
        resp = await client.post(
            "/api/v1/route",
            json={
                "messages": [
                    {"role": "user", "content": SAMPLE_JSON},
                    {"role": "user", "content": SAMPLE_PYTHON},
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_messages"] == 2
        assert len(data["type_distribution"]) >= 1
        assert len(data["messages"]) == 2
        # First message should be detected as JSON
        assert data["messages"][0]["content_type"] == "json"

    @pytest.mark.asyncio
    async def test_route_empty_messages_rejected(self, client):
        resp = await client.post("/api/v1/route", json={"messages": []})
        assert resp.status_code == 422  # validation error

    @pytest.mark.asyncio
    async def test_route_detect_single_json(self, client):
        resp = await client.post(
            "/api/v1/route/detect",
            json={"content": SAMPLE_JSON},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["content_type"] == "json"
        assert data["confidence"] >= 0.5
        assert "json" in data["scores"]

    @pytest.mark.asyncio
    async def test_route_detect_single_code(self, client):
        resp = await client.post(
            "/api/v1/route/detect",
            json={"content": SAMPLE_PYTHON},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["content_type"] == "code"

    @pytest.mark.asyncio
    async def test_route_detect_single_text(self, client):
        resp = await client.post(
            "/api/v1/route/detect",
            json={"content": SAMPLE_PLAIN_TEXT},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["content_type"] == "text"

    @pytest.mark.asyncio
    async def test_route_detect_empty_rejected(self, client):
        resp = await client.post(
            "/api/v1/route/detect",
            json={"content": ""},
        )
        assert resp.status_code == 422
