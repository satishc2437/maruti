"""OneNote MCP Server - Tool metadata and implementations (scaffold + graph_client integration + traversal stub).

Phase:
  - read_onenote_page delegates to graph_client.read_page.
  - write_onenote_page delegates to graph_client.write_page.
  - list_onenote_page_children delegates to graph_client.list_page_children.
  - traverse_onenote_notebook (NEW) delegates to graph_client.traverse_notebook to build hierarchical notebook tree
    with optional per-page truncated content in modes summary|plain|html (scaffold simulated).

Remaining future work:
  * Replace simulated graph_client with real HTTP Graph calls.
  * Add HTML sanitization (sanitize_html) before write.
  * Add richer JSON block parsing for read (paragraph/image/table segmentation).
  * Implement real traversal using sections, sectionGroups, pages endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from .errors import user_input_error
from .graph_client import (list_page_children, read_page, resolve_share_link,
                           traverse_notebook, write_page)
from .safety import validate_content_html, validate_share_link

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool Metadata
# ---------------------------------------------------------------------------

TOOL_METADATA: Dict[str, Dict[str, Any]] = {
    "read_onenote_page": {
        "description": "Read a OneNote page given a share link. Returns plain text, HTML, or JSON structural summary.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "share_link": {
                    "type": "string",
                    "description": "Edit-capable OneNote page share link"
                },
                "format": {
                    "type": "string",
                    "enum": ["plain", "html", "json"],
                    "default": "plain",
                    "description": "Output representation format"
                },
                "include_images": {
                    "type": "boolean",
                    "default": False,
                    "description": "If true, include image placeholder metadata list"
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Optional max character limit for extracted plain text"
                }
            },
            "required": ["share_link"]
        }
    },
    "write_onenote_page": {
        "description": "Write changes to OneNote: replace, append, or create new page (mode).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "share_link": {
                    "type": "string",
                    "description": "Share link of target page (replace/append) or section (new_page)"
                },
                "mode": {
                    "type": "string",
                    "enum": ["replace", "append", "new_page"],
                    "default": "append",
                    "description": "Write operation mode"
                },
                "content_html": {
                    "type": "string",
                    "description": "HTML fragment or full body (required for all current modes)"
                },
                "title": {
                    "type": "string",
                    "description": "Optional title (used for new_page or replace if provided)"
                },
                "position": {
                    "type": "string",
                    "enum": ["top", "bottom"],
                    "default": "bottom",
                    "description": "Insertion point for append mode"
                }
            },
            "required": ["share_link", "content_html"]
        }
    },
    "list_onenote_page_children": {
        "description": "List structural child elements (images/outlines) of a OneNote page or section reference.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "share_link": {
                    "type": "string",
                    "description": "OneNote page or section share link"
                },
                "type": {
                    "type": "string",
                    "enum": ["images", "outlines", "all"],
                    "default": "all",
                    "description": "Filter which child element types are returned"
                }
            },
            "required": ["share_link"]
        }
    },
    "traverse_onenote_notebook": {
        "description": "Traverse an entire OneNote hierarchy (sections, groups, pages, subpages) from a notebook/section share link.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "share_link": {
                    "type": "string",
                    "description": "Notebook or section share link (edit-capable)"
                },
                "content_mode": {
                    "type": "string",
                    "enum": ["summary", "plain", "html"],
                    "default": "summary",
                    "description": "Per-page content inclusion: summary (metadata only), plain (truncated text), html (truncated HTML)"
                },
                "max_chars_per_page": {
                    "type": "integer",
                    "default": 2000,
                    "description": "Max characters for per-page content when content_mode != summary (min 100, max 10000)"
                }
            },
            "required": ["share_link"]
        }
    }
}

# ---------------------------------------------------------------------------
# Validation Helpers
# ---------------------------------------------------------------------------

def _require_share_link(params: Dict[str, Any]) -> str:
    link = params.get("share_link")
    if not link or not isinstance(link, str):
        raise ValueError("Parameter 'share_link' is required and must be a string")
    if len(link) > 2048:
        raise ValueError("Share link appears too long (exceeds 2048 chars)")
    try:
        validate_share_link(link)
    except ValueError as e:
        raise ValueError(str(e))
    return link

# ---------------------------------------------------------------------------
# Tool Implementations
# ---------------------------------------------------------------------------

async def tool_read_onenote_page(params: Dict[str, Any]) -> Dict[str, Any]:
    """Tool: Read a OneNote page (scaffold placeholder)."""
    try:
        share_link = _require_share_link(params or {})
    except ValueError as e:
        return user_input_error(str(e), hint="Provide a valid OneNote page share link")
    fmt = params.get("format", "plain")
    include_images = bool(params.get("include_images", False))
    max_chars = params.get("max_chars")
    if max_chars is not None and not isinstance(max_chars, int):
        return user_input_error("max_chars must be integer if provided")
    return read_page(share_link, fmt, include_images, max_chars)

async def tool_write_onenote_page(params: Dict[str, Any]) -> Dict[str, Any]:
    """Tool: Write to a OneNote page (scaffold placeholder)."""
    try:
        share_link = _require_share_link(params or {})
    except ValueError as e:
        return user_input_error(str(e), hint="Provide a valid page/section share link")
    mode = params.get("mode", "append")
    if mode not in ("replace", "append", "new_page"):
        return user_input_error("Invalid 'mode'", hint="Use replace | append | new_page")
    position = params.get("position", "bottom")
    if position not in ("top", "bottom"):
        return user_input_error("Invalid 'position'", hint="Use top | bottom")
    content_html = params.get("content_html")
    if not isinstance(content_html, str) or not content_html.strip():
        return user_input_error("content_html must be non-empty HTML string")
    length_error = validate_content_html(content_html)
    if length_error:
        return length_error
    title = params.get("title")
    if title is not None and not isinstance(title, str):
        return user_input_error("title must be a string if provided")
    return write_page(share_link, mode, content_html, title, position)

async def tool_list_onenote_page_children(params: Dict[str, Any]) -> Dict[str, Any]:
    """Tool: List children of a OneNote page (scaffold placeholder)."""
    try:
        share_link = _require_share_link(params or {})
    except ValueError as e:
        return user_input_error(str(e), hint="Provide a valid page share link")
    filter_type = params.get("type", "all")
    if filter_type not in ("images", "outlines", "all"):
        return user_input_error("Invalid 'type'", hint="Use images | outlines | all")
    return list_page_children(share_link, filter_type)

async def tool_traverse_onenote_notebook(params: Dict[str, Any]) -> Dict[str, Any]:
    """Traverse entire notebook hierarchy (scaffold)."""
    try:
        share_link = _require_share_link(params or {})
    except ValueError as e:
        return user_input_error(str(e), hint="Provide a valid notebook/section share link")

    content_mode = params.get("content_mode", "summary")
    if content_mode not in ("summary", "plain", "html"):
        return user_input_error("Invalid 'content_mode'", hint="Use summary | plain | html")

    max_chars_per_page = params.get("max_chars_per_page", 2000)
    if not isinstance(max_chars_per_page, int):
        return user_input_error("max_chars_per_page must be integer")
    if max_chars_per_page < 100 or max_chars_per_page > 10000:
        return user_input_error("max_chars_per_page out of range", hint="100 - 10000")

    # Delegate to graph_client scaffold
    return traverse_notebook(share_link, content_mode, max_chars_per_page)

# Map tool name to coroutine
TOOL_DISPATCH = {
    "read_onenote_page": tool_read_onenote_page,
    "write_onenote_page": tool_write_onenote_page,
    "list_onenote_page_children": tool_list_onenote_page_children,
    "traverse_onenote_notebook": tool_traverse_onenote_notebook,
}
