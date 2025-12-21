"""Safety & validation utilities for OneNote MCP server (scaffold).

Responsibilities:
  * Share link validation (pattern + length)
  * Rate limiting (in-memory leaky bucket placeholder)
  * HTML content length & (future) sanitization hook
  * Guard functions used by tool adapters before Graph access

Note:
  Network & real Graph calls not implemented yet. Rate limiting
  currently enforced in-memory and resets on process restart.

Future:
  - Integrate actual HTML sanitization via html_sanitizer.sanitize_html()
  - Persist rate limit counters per time window if needed
  - Add optional streaming read with incremental validation
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict

from .config import (MAX_CONTENT_HTML_CHARS, MAX_PLAINTEXT_EXTRACT_CHARS,
                     RATE_LIMIT_MAX_CALLS, RATE_LIMIT_WINDOW_SECONDS,
                     is_valid_share_link)
from .errors import forbidden_error, user_input_error

# -----------------------------------------------------------------------------
# Share Link Validation
# -----------------------------------------------------------------------------


def validate_share_link(link: str):
    """Validate OneNote share link (pattern + length).

    Raises:
        ValueError: If the share link is invalid.
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
_rate_window: Dict[str, float | int] | tuple[float, int] = {
    "window_start": time.time(),
    "count": 0,
}


def check_rate_limit() -> Dict[str, Any] | None:
    """Enforce simple call rate limit.

    Returns:
        An error dict (UserInput) if exceeded, otherwise None.
    """
    now = time.time()
    with _rate_lock:
        if isinstance(_rate_window, tuple):
            window_start = float(_rate_window[0])
            count = int(_rate_window[1])
        else:
            window_start = float(_rate_window["window_start"])
            count = int(_rate_window["count"])
        if now - window_start >= RATE_LIMIT_WINDOW_SECONDS:
            # reset window
            globals()["_rate_window"] = {"window_start": now, "count": 1}
            return None
        # same window
        if count + 1 > RATE_LIMIT_MAX_CALLS:
            retry_in = max(0, RATE_LIMIT_WINDOW_SECONDS - (now - window_start))
            return user_input_error(
                "Rate limit exceeded",
                hint=f"Allowed {RATE_LIMIT_MAX_CALLS} calls per {RATE_LIMIT_WINDOW_SECONDS}s. Retry in ~{int(retry_in)}s",
            )
        # increment
        if isinstance(_rate_window, tuple):
            globals()["_rate_window"] = {"window_start": window_start, "count": count + 1}
        else:
            _rate_window["count"] = count + 1
    return None


def rate_limit_status() -> Dict[str, Any]:
    """Return the current in-memory rate limiter status."""
    with _rate_lock:
        if isinstance(_rate_window, tuple):
            window_start = float(_rate_window[0])
            count = int(_rate_window[1])
        else:
            window_start = float(_rate_window["window_start"])
            count = int(_rate_window["count"])
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
    """Validate raw HTML length before write operation.

    Returns:
        An error dict if invalid, otherwise None.
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
    """Sanitize HTML content (scaffold placeholder).

    Currently returns original HTML unchanged if the optional sanitizer is not
    available (DO NOT rely on this for security).
    """
    try:
        from .html_sanitizer import sanitize_html as real_sanitize
    except ImportError:
        return html
    return real_sanitize(html)


# -----------------------------------------------------------------------------
# Plain Text Truncation
# -----------------------------------------------------------------------------


def truncate_plaintext(text: str, max_chars: int | None) -> str:
    """Truncate plain text to a safe maximum size."""
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
    """Return a snapshot of safety limits and rate limit status."""
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
