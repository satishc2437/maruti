"""
OneNote MCP Server - server setup & JSON-RPC stdio integration.

Current phase: Scaffold (network + Microsoft Graph not implemented yet).
Tools are registered and return placeholder / stub responses from tools.py.

Run:
  uvx python -m onenote_reader

After full implementation:
  * graph_client.py will perform share link resolution & Graph calls
  * auth.py will manage device code OAuth (in-memory token only)
  * safety.py will enforce rate limiting & share link validation
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List

# Attempt MCP imports (expect user to install `mcp` package)
try:
    from mcp.server import Server
    from mcp.types import Tool, Resource, TextContent
except ImportError as e:
    raise ImportError(
        "MCP library not installed. Install with: pip install mcp"
    ) from e

from .tools import TOOL_METADATA, TOOL_DISPATCH
from .errors import internal_error, ensure_error

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("onenote_reader.server")

# -----------------------------------------------------------------------------
# MCP Server Instance
# -----------------------------------------------------------------------------
server = Server("onenote-reader")


# -----------------------------------------------------------------------------
# Tool Listing
# -----------------------------------------------------------------------------
@server.list_tools()
async def list_tools() -> list[Tool]:
    tools: list[Tool] = []
    for name, meta in TOOL_METADATA.items():
        tools.append(
            Tool(
                name=name,
                description=meta.get("description", ""),
                inputSchema=meta.get("inputSchema", {"type": "object"}),
            )
        )
    logger.info("Listed %d tools", len(tools))
    return tools


# -----------------------------------------------------------------------------
# Tool Invocation
# -----------------------------------------------------------------------------
@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """
    Dispatch tool call.

    Always returns a list[TextContent] whose text is a JSON object containing:
      { ok: bool, ... }
    """
    if not isinstance(arguments, dict):
        arguments = {}

    logger.info("Tool call requested name=%s args=%s", name, json.dumps(arguments)[:500])

    try:
        handler = TOOL_DISPATCH.get(name)
        if handler is None:
            result = {
                "ok": False,
                "code": "UserInput",
                "message": f"Unknown tool: {name}",
                "hint": f"Available: {', '.join(sorted(TOOL_DISPATCH.keys()))}",
            }
        else:
            result = await handler(arguments)

        if not isinstance(result, dict) or "ok" not in result:
            # Defensive normalization
            result = {"ok": True, "data": result}

        content = TextContent(type="text", text=json.dumps(result, indent=2, default=str))
        return [content]

    except Exception as exc:
        logger.exception("Unhandled exception in tool %s", name)
        err = internal_error("Tool execution failed", detail=str(exc))
        content = TextContent(type="text", text=json.dumps(err, indent=2))
        return [content]


# -----------------------------------------------------------------------------
# Resources
# -----------------------------------------------------------------------------
@server.list_resources()
async def list_resources() -> list[Resource]:
    resources = [
        Resource(
            uri="onenote://server-status",
            name="Server Status",
            description="Runtime status & registered tools",
        ),
        Resource(
            uri="onenote://capabilities",
            name="Capabilities",
            description="Declared capabilities and limits",
        ),
    ]
    return resources


@server.read_resource()
async def read_resource(uri: str) -> str:
    if uri == "onenote://server-status":
        payload = {
            "server": "onenote-reader",
            "version": "0.0.1-scaffold",
            "tools": list(TOOL_METADATA.keys()),
            "auth": {
                "device_code_flow": "planned",
                "token_cached": False,
                "storage": "memory-only",
            },
            "phase": "scaffold",
        }
        return json.dumps(payload, indent=2)
    if uri == "onenote://capabilities":
        payload = {
            "read_page": True,
            "write_page": True,
            "list_children": True,
            "traverse_notebook": True,
            "streaming": False,
            "html_sanitization": "planned",
            "rate_limit": "5 calls / 10s (planned enforcement)",
            "max_content_html": 100000,
            "max_plaintext_chars": 200000,
            "traversal": {
                "content_modes": ["summary", "plain", "html"],
                "default_max_chars_per_page": 2000,
                "implemented": "scaffold-simulated"
            },
            "allowed_html_tags_subset": [
                "p",
                "div",
                "h1",
                "h2",
                "h3",
                "h4",
                "ul",
                "ol",
                "li",
                "strong",
                "em",
                "a",
                "img",
                "br",
                "span",
                "table",
                "tr",
                "td",
                "th",
            ],
        }
        return json.dumps(payload, indent=2)
    raise ValueError(f"Unknown resource URI: {uri}")


# -----------------------------------------------------------------------------
# Server Run Loop
# -----------------------------------------------------------------------------
async def run_server():
    """
    Start MCP server over stdio transport.
    """
    logger.info("Starting OneNote MCP server (scaffold)...")
    try:
        from mcp.server.stdio import stdio_server
    except Exception as e:
        logger.error("Failed importing stdio transport: %s", e)
        raise

    async with stdio_server() as (read_stream, write_stream):
        logger.info("OneNote server ready (awaiting client)...")
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


# -----------------------------------------------------------------------------
# Lightweight dev test
# -----------------------------------------------------------------------------
async def test_server():
    logger.info("Running basic self-test...")
    tools = await list_tools()
    logger.info("Tools: %s", [t.name for t in tools])
    status = await read_resource("onenote://server-status")
    logger.info("Server status: %s", status)
    logger.info("Self-test complete.")


if __name__ == "__main__":
    # Allow quick manual execution
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        asyncio.run(test_server())
    else:
        asyncio.run(run_server())