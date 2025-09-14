"""
Configuration constants for OneNote MCP server (scaffold phase).

Centralizes limits, allowed hosts, HTML sanitation policy, and rate limit
defaults so future implementation modules (auth, graph_client, safety,
tools) can import from a single place.

No dynamic loading yet; future enhancement could add JSON/TOML reload.
"""

from __future__ import annotations

import re
from typing import Final, Pattern, List

VERSION: Final[str] = "0.0.1-scaffold"

# Rate limiting (planned enforcement)
RATE_LIMIT_MAX_CALLS: Final[int] = 5
RATE_LIMIT_WINDOW_SECONDS: Final[int] = 10

# Content limits
MAX_CONTENT_HTML_CHARS: Final[int] = 100_000
MAX_PLAINTEXT_EXTRACT_CHARS: Final[int] = 200_000

# Allowed Microsoft Graph hosts (network operations will be restricted to these)
ALLOWED_GRAPH_HOSTS: Final[List[str]] = [
    "graph.microsoft.com",
]

# Allowed path prefixes (future use for stricter validation)
ALLOWED_GRAPH_PREFIXES: Final[List[str]] = [
    "/v1.0/me/onenote",
    "/v1.0/shares",
]

# Share link validation (basic patterns - future refinement)
SHARE_LINK_PATTERNS: Final[List[Pattern[str]]] = [
    re.compile(r"^https://1drv\.ms/"),
    re.compile(r"https://.*onenote\.com/"),
    re.compile(r"https://.*onenote\.officeapps\.live\.com/"),
]

# HTML sanitation policy (subset)
ALLOWED_HTML_TAGS: Final[List[str]] = [
    "p", "div", "h1", "h2", "h3", "h4",
    "ul", "ol", "li",
    "strong", "em", "a",
    "img", "br", "span",
    "table", "tr", "td", "th"
]

# Allowed attributes per tag (conservative)
ALLOWED_ATTRS: Final[dict[str, List[str]]] = {
    "a": ["href", "title"],
    "img": ["src", "alt", "title"],
    "table": ["border"],
    # common global subset (will be filtered explicitly)
    "p": [],
    "div": [],
    "span": [],
    "strong": [],
    "em": [],
    "ul": [],
    "ol": [],
    "li": [],
    "h1": [], "h2": [], "h3": [], "h4": [],
    "tr": [], "td": [], "th": [],
    "br": [],
}

# Disallowed (strip) - style & script
STRIP_TAGS: Final[List[str]] = [
    "script", "style", "iframe", "object", "embed"
]

# Simple user agent (Graph may accept default; placeholder)
USER_AGENT: Final[str] = "onenote-mcp-scaffold/0.0.1"

# HTTP per-request timeout seconds (planned)
HTTP_TIMEOUT_SECONDS: Final[float] = 15.0


def is_valid_share_link(link: str) -> bool:
    """
    Return True if share link matches any accepted pattern.
    """
    if not isinstance(link, str) or len(link) > 2048:
        return False
    return any(p.search(link) for p in SHARE_LINK_PATTERNS)


__all__ = [
    "VERSION",
    "RATE_LIMIT_MAX_CALLS",
    "RATE_LIMIT_WINDOW_SECONDS",
    "MAX_CONTENT_HTML_CHARS",
    "MAX_PLAINTEXT_EXTRACT_CHARS",
    "ALLOWED_GRAPH_HOSTS",
    "ALLOWED_GRAPH_PREFIXES",
    "SHARE_LINK_PATTERNS",
    "ALLOWED_HTML_TAGS",
    "ALLOWED_ATTRS",
    "STRIP_TAGS",
    "USER_AGENT",
    "HTTP_TIMEOUT_SECONDS",
    "is_valid_share_link",
]