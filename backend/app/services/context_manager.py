"""Conversation Context Manager for LLM Context Window Optimization.

Features
--------
1. Maximum Context Budget: Enforces token ceilings to avoid prompt bloat.
2. Rolling Window & Recent-Message Preservation: Retains the latest N messages verbatim.
3. System Message Preservation: Always pins system prompt instructions.
4. Important Message Preservation: Retains key instruction landmarks and errors.
5. Older Context Summarization: Generates structured summaries of evicted older messages.
6. CCR Archiving: Automatically archives older conversation segments into SQLite CCR storage
   and inserts a retrieval token [CCR:ctx_xxx].
7. Real Gemini Token Counting: Uses official Gemini count_tokens API for accurate measurements.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.chat import Message
from app.services.token_analyzer import estimate_tokens
from app.services.ccr_service import ccr_service
from app.services.content_router import ContentRouter
from app.services.compressors import get_compressor

logger = logging.getLogger(__name__)


class ContextManager:
    """Intelligently manages conversation history for LLM generation."""

    DEFAULT_MAX_CONTEXT_TOKENS = 3000
    DEFAULT_RECENT_COUNT = 4

    def __init__(self) -> None:
        self.router = ContentRouter()

    async def optimize_context(
        self,
        messages: list[dict[str, str]],
        *,
        max_context_tokens: Optional[int] = None,
        recent_count: Optional[int] = None,
        preserve_system: bool = True,
        archive_to_ccr: bool = True,
        db: Optional[AsyncSession] = None,
        provider = None,
        model: str = "gemini-3.6-flash",
    ) -> tuple[list[dict[str, str]], dict[str, Any]]:
        """Optimize conversation history to fit within target token budget.

        Uses REAL Gemini token counting via the official count_tokens API.

        Parameters
        ----------
        messages : list[dict]
            List of `{"role": ..., "content": ...}` dicts.
        max_context_tokens : int, optional
            Token ceiling for the total conversation context.
        recent_count : int, optional
            Number of recent messages to preserve untouched.
        preserve_system : bool
            Whether system prompts must always be kept at the head.
        archive_to_ccr : bool
            Whether to archive older evicted turns into SQLite CCR storage.
        db : AsyncSession, optional
            Database session for CCR persistence.
        provider : GeminiProvider, optional
            Provider instance for real token counting.
        model : str
            Model name for token counting.
        """
        if not messages:
            return [], {
                "original_tokens": 0,
                "optimized_tokens": 0,
                "tokens_saved": 0,
                "compression_ratio": 1.0,
                "original_message_count": 0,
                "optimized_message_count": 0,
                "summary_injected": False,
                "archived_context_id": None,
                "strategy": "empty_input",
            }

        max_tokens = max_context_tokens or self.DEFAULT_MAX_CONTEXT_TOKENS
        recent_n = recent_count if recent_count is not None else self.DEFAULT_RECENT_COUNT

        # Get REAL Gemini token count for original messages
        if provider:
            try:
                total_original_tokens = await provider.count_tokens(
                    messages=messages,
                    model=model,
                )
            except Exception as e:
                logger.warning(f"Failed to get real Gemini token count, using heuristic: {e}")
                total_original_tokens = sum(estimate_tokens(m.get("content", "")) for m in messages)
        else:
            # Fallback to heuristic if provider not available
            total_original_tokens = sum(estimate_tokens(m.get("content", "")) for m in messages)
        original_msg_count = len(messages)
        MIN_OPTIMIZATION_TOKENS = 1000

        # Bypass optimization only if context is small AND already fits within budget
        if total_original_tokens < MIN_OPTIMIZATION_TOKENS and total_original_tokens <= max_tokens:
            return messages, {
                "original_tokens": total_original_tokens,
                "optimized_tokens": total_original_tokens,
                "tokens_saved": 0,
                "compression_ratio": 1.0,
                "original_message_count": original_msg_count,
                "optimized_message_count": original_msg_count,
                "summary_injected": False,
                "archived_context_id": None,
                "strategy": "bypass_small_context",
            }

        # 1. Content-level compression: optimize large payloads (JSON, Code, Logs) within individual messages
        compressed_turns: list[dict[str, str]] = []
        for m in messages:
            content = m.get("content", "")
            if len(content) >= 150:
                det = self.router.detect(content)
                if det.confidence >= 0.30 and det.content_type.value in ("json", "code", "logs"):
                    comp = get_compressor(det.content_type.value)
                    if comp:
                        c_res = comp.compress(content)
                        if c_res.compression_ratio < 0.85:
                            compressed_turns.append({"role": m.get("role", "user"), "content": c_res.compressed_content})
                            continue
            compressed_turns.append(m)

        working_messages = compressed_turns

        # Get REAL Gemini token count for working messages after compression
        if provider:
            try:
                working_tokens = await provider.count_tokens(
                    messages=working_messages,
                    model=model,
                )
            except Exception as e:
                logger.warning(f"Failed to get real Gemini token count for working messages: {e}")
                working_tokens = sum(estimate_tokens(m.get("content", "")) for m in working_messages)
        else:
            working_tokens = sum(estimate_tokens(m.get("content", "")) for m in working_messages)

        # If within token budget, return optimized working messages
        if working_tokens <= max_tokens:
            tokens_saved = max(0, total_original_tokens - working_tokens)
            ratio = round(working_tokens / max(1, total_original_tokens), 4)
            return working_messages, {
                "original_tokens": total_original_tokens,
                "optimized_tokens": working_tokens,
                "tokens_saved": tokens_saved,
                "compression_ratio": ratio,
                "original_message_count": original_msg_count,
                "optimized_message_count": len(working_messages),
                "summary_injected": False,
                "archived_context_id": None,
                "strategy": "content_compression_within_budget" if tokens_saved > 0 else "passthrough_within_budget",
            }

        # 2. Partition messages into System, Older Turns, and Recent Window
        system_messages: list[dict[str, str]] = []
        conversation_turns: list[dict[str, str]] = []

        for m in working_messages:
            if m.get("role") == "system" and preserve_system:
                system_messages.append(m)
            else:
                conversation_turns.append(m)

        # Protected recent window
        if len(conversation_turns) <= recent_n:
            recent_turns = conversation_turns
            older_turns = []
        else:
            older_turns = conversation_turns[:-recent_n]
            recent_turns = conversation_turns[-recent_n:]

        # If there are no older turns to compress, return as is
        if not older_turns:
            optimized = system_messages + recent_turns
            opt_tokens = sum(estimate_tokens(m.get("content", "")) for m in optimized)
            return optimized, {
                "original_tokens": total_original_tokens,
                "optimized_tokens": opt_tokens,
                "tokens_saved": max(0, total_original_tokens - opt_tokens),
                "compression_ratio": round(opt_tokens / max(1, total_original_tokens), 4),
                "original_message_count": original_msg_count,
                "optimized_message_count": len(optimized),
                "summary_injected": False,
                "archived_context_id": None,
                "strategy": "recent_window_only",
            }

        # 3. Identify Important Landmarks in Older Turns
        important_turns, regular_older_turns = self._extract_important_turns(older_turns)

        # 4. Archive Older Turns to CCR if requested and DB session available
        archived_ctx_id: Optional[str] = None
        if archive_to_ccr and db is not None:
            older_payload = json.dumps(older_turns, indent=2)
            ccr_record = await ccr_service.store_context(
                db,
                content=older_payload,
                content_type="conversation",
                description=f"Older conversation archive ({len(older_turns)} messages)",
            )
            archived_ctx_id = ccr_record.context_id

        # 5. Generate Structured Extractive Summary of Older Turns
        summary_text = self._build_conversation_summary(
            regular_older_turns,
            archived_context_id=archived_ctx_id,
        )

        # Use system role for summary to avoid creating fake conversation history
        summary_message = {
            "role": "system",
            "content": f"[Context Manager - Prior History Summary]\n{summary_text}",
        }

        # 5. Assemble Optimized Message Stream
        optimized_messages: list[dict[str, str]] = []
        optimized_messages.extend(system_messages)
        optimized_messages.append(summary_message)
        optimized_messages.extend(important_turns)
        optimized_messages.extend(recent_turns)

        # Get REAL Gemini token count for final optimized messages
        if provider:
            try:
                optimized_tokens = await provider.count_tokens(
                    messages=optimized_messages,
                    model=model,
                )
            except Exception as e:
                logger.warning(f"Failed to get real Gemini token count for optimized messages: {e}")
                optimized_tokens = sum(estimate_tokens(m.get("content", "")) for m in optimized_messages)
        else:
            optimized_tokens = sum(estimate_tokens(m.get("content", "")) for m in optimized_messages)

        tokens_saved = max(0, total_original_tokens - optimized_tokens)
        ratio = round(optimized_tokens / max(1, total_original_tokens), 4)

        metrics = {
            "original_tokens": total_original_tokens,
            "optimized_tokens": optimized_tokens,
            "tokens_saved": tokens_saved,
            "compression_ratio": ratio,
            "original_message_count": original_msg_count,
            "optimized_message_count": len(optimized_messages),
            "summary_injected": True,
            "archived_context_id": archived_ctx_id,
            "older_messages_compressed": len(older_turns),
            "important_messages_preserved": len(important_turns),
            "recent_messages_preserved": len(recent_turns),
            "strategy": "rolling_window_with_summary_and_ccr",
        }

        return optimized_messages, metrics

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _extract_important_turns(
        turns: list[dict[str, str]],
    ) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        """Separate crucial high-signal messages (e.g. errors, critical keys) from regular dialog."""
        important: list[dict[str, str]] = []
        regular: list[dict[str, str]] = []

        for turn in turns:
            content = turn.get("content", "")
            # Heuristics for important landmark turns
            has_error = any(kw in content.lower() for kw in ("exception:", "traceback", "critical error", "failed with code"))
            is_goal_definition = "primary objective:" in content.lower() or "strict requirements:" in content.lower()
            
            if (has_error or is_goal_definition) and len(important) < 2:
                important.append(turn)
            else:
                regular.append(turn)

        return important, regular

    @staticmethod
    def _build_conversation_summary(
    turns: list[dict[str, str]],
    archived_context_id: Optional[str] = None,
) -> str:
        """Create a compact summary of older conversation turns."""
        lines: list[str] = []

        for idx, turn in enumerate(turns):
            role = turn.get("role", "unknown")
            text = turn.get("content", "").strip()

            if not text:
                continue

            first_line = text.split("\n")[0].strip()

        # Keep only the first 100 characters of each older turn.
            first_line = first_line[:100]

            lines.append(f"{role}: {first_line}")

        summary = "\n".join(lines[:6])

        if archived_context_id:
            summary += f"\n[CCR:{archived_context_id}]"

        return summary


# Singleton
context_manager = ContextManager()
