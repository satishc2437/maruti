"""
Safety & validation utilities for OneNote MCP server (scaffold).

Responsibilities:
  * Share link validation (pattern + length)
  * Rate limiting (in-memory leaky bucket placeholder)
  * HTML content length & (future) sanitization hook
  * Guard functions used by tool adapters before Graph access

NOTE:
  Network & real Graph calls not implemented yet. Rate limiting
  currently enforced in-memory and resets on process restart.

Future:
  - Integrate actual HTML sanitization via html_sanitizer.sanitize_html()
  - Persist rate limit counters per time window if needed
  - Add optional streaming read with incremental validation
"""

from __future__ import annotations

import time
import threading
from typing import Dict, Any, Tuple

from .config import (
    is_valid_share_link,
    MAX_CONTENT_HTML_CHARS,
    MAX_PLAINTEXT_EXTRACT_CHARS,
    RATE_LIMIT_MAX_CALLS,
    RATE_LIMIT_WINDOW_SECONDS,
)

from .errors import user_input_error, forbidden_error

# -----------------------------------------------------------------------------
# Share Link Validation
# -----------------------------------------------------------------------------


def validate_share_link(link: str):
    """
    Validate OneNote share link (pattern + length). Return None if ok
    else raise ValueError for uniform handling in callers.
    """
    if not isinstance(link, str):
        raise ValueError("Share link must be a string")
    if len(link) == 0:
        raise ValueError("Share link cannot be empty")
    if len(link) > 2048:
        raise ValueError("Share link exceeds maximum length (2048)")
    if not is_valid_share_link(link):
        raise ValueError("Share link does not match accepted OneNote patterns")


# -----------------------------------------------------------------------------
# Rate Limiter (simple leaky bucket)
# -----------------------------------------------------------------------------
_rate_lock = threading.RLock()
# window_start: float, count: int
_rate_window: Tuple[float, int] = (time.time(), 0)


def check_rate_limit() -> Dict[str, Any] | None:
    """
    Enforce simple call rate limit.
    Returns error dict (UserInput) if exceeded else None.
    """
    global _rate_window
    now = time.time()
    with _rate_lock:
        window_start, count = _rate_window
        if now - window_start >= RATE_LIMIT_WINDOW_SECONDS:
            # reset window
            _rate_window = (now, 1)
            return None
        # same window
        if count + 1 > RATE_LIMIT_MAX_CALLS:
            remaining = 0
            retry_in = max(0, RATE_LIMIT_WINDOW_SECONDS - (now - window_start))
            return user_input_error(
                "Rate limit exceeded",
                hint=f"Allowed {RATE_LIMIT_MAX_CALLS} calls per {RATE_LIMIT_WINDOW_SECONDS}s. Retry in ~{int(retry_in)}s",
            )
        # increment
        _rate_window = (window_start, count + 1)
    return None


def rate_limit_status() -> Dict[str, Any]:
    with _rate_lock:
        window_start, count = _rate_window
        elapsed = time.time() - window_start
        remaining_time = max(0, RATE_LIMIT_WINDOW_SECONDS - elapsed)
        remaining_calls = max(0, RATE_LIMIT_MAX_CALLS - count)
        return {
            "window_seconds": RATE_LIMIT_WINDOW_SECONDS,
            "used": count,
            "remaining_calls": remaining_calls,
            "reset_in_seconds": int(remaining_time),
        }


# -----------------------------------------------------------------------------
# HTML Content Validation / Sanitization (placeholder)
# -----------------------------------------------------------------------------


def validate_content_html(html: str) -> Dict[str, Any] | None:
    """
    Validate raw HTML length before write operation.
    Returns error dict if invalid else None.
    """
    if not isinstance(html, str):
        return user_input_error("content_html must be a string")
    if not html.strip():
        return user_input_error("content_html cannot be empty/whitespace")
    if len(html) > MAX_CONTENT_HTML_CHARS:
        return user_input_error(
            "content_html exceeds maximum length",
            hint=f"Max {MAX_CONTENT_HTML_CHARS} characters allowed",
        )
    return None


def sanitize_html(html: str) -> str:
    """
    Placeholder sanitizer: will integrate with html_sanitizer.sanitize_html later.
    Currently returns original html unchanged (DO NOT rely on this for security).
    """
    try:
        from .html_sanitizer import sanitize_html as real_sanitize  # type: ignore
        return real_sanitize(html)
    except Exception:
        # Fallback to original (non-sanitized) - acceptable only in scaffold phase.
        return html


# -----------------------------------------------------------------------------
# Plain Text Truncation
# -----------------------------------------------------------------------------


def truncate_plaintext(text: str, max_chars: int | None) -> str:
    if not isinstance(text, str):
        return ""
    cap = max_chars if isinstance(max_chars, int) and max_chars > 0 else MAX_PLAINTEXT_EXTRACT_CHARS
    if len(text) <= cap:
        return text
    return text[: cap - 3] + "..."


# -----------------------------------------------------------------------------
# Public Summary Utility
# -----------------------------------------------------------------------------


def safety_status() -> Dict[str, Any]:
    rl = rate_limit_status()
    return {
        "rate_limit": rl,
        "limits": {
            "max_content_html_chars": MAX_CONTENT_HTML_CHARS,
            "max_plaintext_extract_chars": MAX_PLAINTEXT_EXTRACT_CHARS,
        },
        "auth": {
            "device_code_flow": "planned",
            "token_cache": "memory-only",
        },
        "phase": "scaffold",
    }


__all__ = [
    "validate_share_link",
    "check_rate_limit",
    "rate_limit_status",
    "validate_content_html",
    "sanitize_html",
    "truncate_plaintext",
    "safety_status",
]