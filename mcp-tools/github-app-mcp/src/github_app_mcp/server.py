"""MCP server wiring for github-app-mcp.

Phase 1 provides a server that can start, list tools/resources, and safely
serialize results.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

try:
    from mcp.server import Server
    from mcp.types import Resource, TextContent, Tool
except ImportError as exc:  # pragma: no cover
    raise ImportError("MCP library not installed. Install with: pip install mcp") from exc

from . import __version__
from .errors import SafeError, internal_error
from .tools import TOOL_METADATA, dispatch_tool, initialize_runtime_from_env

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

server = Server("github-app-mcp")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    tools: list[Tool] = []
    for tool_name, metadata in TOOL_METADATA.items():
        tools.append(
            Tool(
                name=tool_name,
                description=metadata["description"],
                inputSchema=metadata["inputSchema"],
            )
        )

    logger.info("Listed %s tools", len(tools))
    return tools


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute a tool and return MCP-compliant TextContent."""
    if not isinstance(arguments, dict):
        arguments = {}

    logger.info("Tool called: %s", name)

    try:
        raw_result = await dispatch_tool(name, arguments)
        content = TextContent(type="text", text=json.dumps(raw_result, indent=2, default=str))
        return [content]
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Tool %s failed: %s", name, exc)
        error_result = internal_error("Tool execution failed")
        content = TextContent(type="text", text=json.dumps(error_result, indent=2, default=str))
        return [content]


@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources."""
    return [
        Resource(
            uri="github-app-mcp://server-status",
            name="Server Status",
            description="Non-secret server configuration and limits",
        ),
        Resource(
            uri="github-app-mcp://capabilities",
            name="Capabilities",
            description="Allow-listed operations and safety constraints",
        ),
    ]


@server.read_resource()
async def read_resource(uri: Any) -> str:
    """Read resource content."""
    uri_s = uri if isinstance(uri, str) else str(uri)

    if uri_s == "github-app-mcp://capabilities":
        caps = {
            "server": "github-app-mcp",
            "version": __version__,
            "allow_listed_operations": sorted(TOOL_METADATA.keys()),
            "safety": {
                "no_pats_or_user_tokens": True,
                "no_arbitrary_github_api_calls": True,
                "github_api_host_allowlist": ["https://api.github.com"],
            },
        }
        return json.dumps(caps, indent=2)

    if uri_s == "github-app-mcp://server-status":
        status: dict[str, Any] = {
            "server": "github-app-mcp",
            "version": __version__,
            "tools_available": len(TOOL_METADATA),
            "tool_names": sorted(TOOL_METADATA.keys()),
            "configured": False,
        }
        try:
            runtime = initialize_runtime_from_env()
            status["configured"] = True
            status["limits"] = {
                "total_timeout_s": runtime.config.limits.total_timeout_s,
                "commit_max_files": runtime.config.limits.commit_max_files,
                "commit_max_file_bytes": runtime.config.limits.commit_max_file_bytes,
                "commit_max_total_bytes": runtime.config.limits.commit_max_total_bytes,
                "get_file_max_bytes": runtime.config.limits.get_file_max_bytes,
            }
            status["policy"] = {
                "repo_allowlist_enabled": bool(runtime.config.policy.allowed_repos),
                "repo_allowlist_count": len(runtime.config.policy.allowed_repos),
                "pr_only": runtime.config.policy.pr_only,
                "protected_branch_patterns_count": len(runtime.config.policy.protected_branches),
            }
            status["audit"] = {"file_sink_enabled": runtime.config.audit_log_path is not None}
        except SafeError:
            status["configured"] = False

        return json.dumps(status, indent=2)

    return json.dumps({"ok": False, "code": "NotFound", "message": "Unknown resource"}, indent=2)


async def run_server() -> None:
    """Run the server over stdio."""
    # Fail fast on invalid/missing host configuration.
    try:
        _ = initialize_runtime_from_env()
    except SafeError as exc:
        logger.error("Startup configuration error: %s", exc.message)
        raise

    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


async def test_server() -> None:
    """Lightweight self-test to ensure tool/resource listing works."""
    # Avoid calling decorated handlers directly; just validate we can construct
    # Tool/Resource objects.
    _ = [
        Tool(name=name, description=meta["description"], inputSchema=meta["inputSchema"])
        for name, meta in TOOL_METADATA.items()
    ]
    _ = [
        Resource(
            uri="github-app-mcp://server-status",
            name="Server Status",
            description="Non-secret server configuration and limits",
        ),
        Resource(
            uri="github-app-mcp://capabilities",
            name="Capabilities",
            description="Allow-listed operations and safety constraints",
        ),
    ]
