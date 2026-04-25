"""MCP server setup and registration for {{TOOL_HYPHEN}}.

Handles server initialization, tool registration, and JSON-RPC
communication over stdio.
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List

try:
    from mcp.server import Server
    from mcp.types import TextContent, Tool
except ImportError as exc:  # pragma: no cover
    raise ImportError("MCP library not installed. Install with: pip install mcp") from exc

from .tools import TOOL_METADATA, tool_example_tool


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

server = Server("{{TOOL_HYPHEN}}")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available {{TOOL_HYPHEN}} tools."""
    return [
        Tool(name=name, description=meta["description"], inputSchema=meta["inputSchema"])
        for name, meta in TOOL_METADATA.items()
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Dispatch a tool call and wrap the result in a TextContent envelope."""
    if not isinstance(arguments, dict):
        arguments = {}

    try:
        if name == "example_tool":
            raw_result = await tool_example_tool(arguments)
        else:
            raw_result = {
                "ok": False,
                "code": "UserInput",
                "message": f"Unknown tool: {name}",
                "hint": f"Available tools: {', '.join(TOOL_METADATA.keys())}",
            }

        if not isinstance(raw_result, dict) or "ok" not in raw_result:
            raw_result = {"ok": True, "data": raw_result}

        return [TextContent(type="text", text=json.dumps(raw_result, indent=2, default=str))]

    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Tool %s failed: %s", name, exc)
        error_result = {
            "ok": False,
            "code": "Internal",
            "message": "Tool execution failed",
            "detail": str(exc),
        }
        return [TextContent(type="text", text=json.dumps(error_result, indent=2, default=str))]


async def run_server() -> None:
    """Run the {{TOOL_HYPHEN}} MCP Server over stdio."""
    logger.info("Starting {{TOOL_HYPHEN}} MCP Server")
    try:
        from mcp.server.stdio import stdio_server  # pylint: disable=import-outside-toplevel

        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream, write_stream, server.create_initialization_options()
            )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Server error: %s", exc)
        raise


async def test_server() -> None:
    """Lightweight self-test that lists tools without starting the server loop."""
    tools = await list_tools()
    print(f"Available tools: {[t.name for t in tools]}")


if __name__ == "__main__":  # pragma: no cover
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        asyncio.run(test_server())
    else:
        asyncio.run(run_server())
