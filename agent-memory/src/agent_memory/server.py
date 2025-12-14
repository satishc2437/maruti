"""
MCP Server setup and registration for Agent Memory.

Handles server initialization, tool registration, resource setup,
and JSON-RPC communication over stdio.
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List

# MCP imports
try:
    from mcp.server import Server
    from mcp.types import Resource, TextContent, Tool
except ImportError:
    raise ImportError("MCP library not installed. Install with: pip install mcp")

from .memory_ops import DEFAULT_ALLOWED_SECTIONS, SCHEMA_VERSION
from .tools import (
    TOOL_METADATA,
    tool_append_entry,
    tool_list_sessions,
    tool_read_summary,
    tool_start_session,
    tool_update_summary,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

# Create MCP server instance
server = Server("agent-memory")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available agent memory tools."""
    tools = []

    for tool_name, metadata in TOOL_METADATA.items():
        tool = Tool(
            name=tool_name,
            description=metadata["description"],
            inputSchema=metadata["inputSchema"]
        )
        tools.append(tool)

    logger.info(f"Listed {len(tools)} agent memory tools")
    return tools


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """
    Handle tool execution requests and ensure MCP-compliant response format.

    Always returns list[TextContent] so that the MCP client never receives
    raw dicts (which caused previous Pydantic validation errors complaining
    about missing 'type' / 'text' fields for CallToolResult.content[0]).
    """
    if not isinstance(arguments, dict):
        arguments = {}

    logger.info(f"Tool called: {name} args={json.dumps(arguments, default=str)}")

    try:
        # Dispatch to tool implementations
        if name == "start_session":
            raw_result = await tool_start_session(arguments)
        elif name == "append_entry":
            raw_result = await tool_append_entry(arguments)
        elif name == "read_summary":
            raw_result = await tool_read_summary(arguments)
        elif name == "update_summary":
            raw_result = await tool_update_summary(arguments)
        elif name == "list_sessions":
            raw_result = await tool_list_sessions(arguments)
        else:
            raw_result = {
                "ok": False,
                "code": "UserInput",
                "message": f"Unknown tool: {name}",
                "hint": f"Available tools: {', '.join(TOOL_METADATA.keys())}"
            }

        # Defensive normalization: if a tool accidentally returns a plain list or scalar
        # wrap it in a success envelope so JSON dump is always structured.
        if not isinstance(raw_result, dict) or ("ok" not in raw_result):
            raw_result = {"ok": True, "data": raw_result}

        logger.info(f"Tool {name} completed ok={raw_result.get('ok')} code={raw_result.get('code','')}")

        # Always serialize tool result as JSON string inside TextContent
        content = TextContent(type="text", text=json.dumps(raw_result, indent=2, default=str))
        return [content]

    except Exception as e:
        logger.error(f"Tool {name} failed with unexpected exception: {e}")
        error_result = {
            "ok": False,
            "code": "Internal",
            "message": "Tool execution failed",
            "detail": str(e)
        }
        content = TextContent(type="text", text=json.dumps(error_result, indent=2, default=str))
        return [content]


@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources."""
    resources = [
        Resource(
            uri="memory://schema-info",
            name="Memory Schema Information",
            description="Information about the agent memory schema and allowed sections"
        ),
        Resource(
            uri="memory://server-status",
            name="Server Status",
            description="Current server status and configuration"
        ),
        Resource(
            uri="memory://usage-examples",
            name="Usage Examples",
            description="Example usage patterns for agent memory operations"
        )
    ]

    logger.info(f"Listed {len(resources)} resources")
    return resources


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read resource content."""
    logger.info(f"Resource requested: {uri}")

    if uri == "memory://schema-info":
        schema_info = {
            "schema_version": SCHEMA_VERSION,
            "allowed_sections": DEFAULT_ALLOWED_SECTIONS,
            "repository_structure": {
                "root": ".github/agent-memory/<agent-name>/",
                "logs": "logs/YYYY-MM-DD.md",
                "schema": "_schema.md",
                "summary": "_summary.md"
            },
            "section_descriptions": {
                "Context": "Project context, focus area, and current stage",
                "Discussion Summary": "Key topics discussed during the session",
                "Decisions": "Explicit decisions made during the session",
                "Open Questions": "Unresolved issues, risks, or uncertainties",
                "Next Actions": "Follow-up actions and next steps"
            },
            "design_principles": [
                "Deterministic - No probabilistic behavior",
                "Schema-enforced - All memory follows declared structure",
                "Repo-local - Memory lives inside the consuming Git repository",
                "Agent-safe - Agents read freely, write via explicit tools only",
                "Human-controlled - Humans decide what becomes durable knowledge"
            ]
        }
        return json.dumps(schema_info, indent=2)

    elif uri == "memory://server-status":
        status = {
            "server_name": "Agent Memory MCP Server",
            "version": "1.0.0",
            "schema_version": SCHEMA_VERSION,
            "tools_available": len(TOOL_METADATA),
            "tool_names": list(TOOL_METADATA.keys()),
            "capabilities": [
                "Session management",
                "Structured memory logging",
                "Persistent summaries",
                "Schema validation",
                "Repository-scoped storage"
            ],
            "safety_features": [
                "Path traversal protection",
                "Repository boundary enforcement",
                "Agent name validation",
                "Content sanitization",
                "Schema compliance checking"
            ],
            "limitations": [
                "No delete operations supported",
                "No network access required",
                "No arbitrary shell execution",
                "Memory limited to repository scope"
            ]
        }
        return json.dumps(status, indent=2)

    elif uri == "memory://usage-examples":
        examples = {
            "typical_workflow": [
                "1. Agent session starts",
                "2. Agent reads summary via read_summary",
                "3. Human and agent reason together",
                "4. Important outcomes persisted via append_entry",
                "5. Durable knowledge curated into summary via update_summary"
            ],
            "start_session_example": {
                "tool": "start_session",
                "arguments": {
                    "agent_name": "aristotle",
                    "repo_root": "/path/to/project"
                }
            },
            "append_entry_example": {
                "tool": "append_entry",
                "arguments": {
                    "agent_name": "aristotle",
                    "repo_root": "/path/to/project",
                    "section": "Decisions",
                    "content": "Decided to use React for the frontend framework"
                }
            },
            "read_summary_example": {
                "tool": "read_summary",
                "arguments": {
                    "agent_name": "aristotle",
                    "repo_root": "/path/to/project"
                }
            },
            "update_summary_example": {
                "tool": "update_summary",
                "arguments": {
                    "agent_name": "aristotle",
                    "repo_root": "/path/to/project",
                    "section": "Key Knowledge",
                    "content": "Frontend architecture: React with TypeScript, using Vite for build tooling",
                    "mode": "append"
                }
            },
            "list_sessions_example": {
                "tool": "list_sessions",
                "arguments": {
                    "agent_name": "aristotle",
                    "repo_root": "/path/to/project",
                    "limit": 10
                }
            }
        }
        return json.dumps(examples, indent=2)

    else:
        raise ValueError(f"Unknown resource URI: {uri}")


async def run_server():
    """Run the Agent Memory MCP Server."""
    logger.info("Starting Agent Memory MCP Server...")

    # Log available tools
    logger.info(f"Registered tools: {', '.join(TOOL_METADATA.keys())}")
    logger.info(f"Schema version: {SCHEMA_VERSION}")

    try:
        # Run server with stdio transport
        from mcp.server.stdio import stdio_server

        logger.info("Agent Memory MCP Server ready for connections")
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


# For direct testing
async def test_server():
    """Simple test function for development."""
    logger.info("Running server tests...")

    # Test tool listing
    tools = await list_tools()
    print(f"Available tools: {[t.name for t in tools]}")

    # Test resource listing
    resources = await list_resources()
    print(f"Available resources: {[r.name for r in resources]}")

    # Test resource reading
    status = await read_resource("memory://server-status")
    print(f"Server status: {status}")

    schema_info = await read_resource("memory://schema-info")
    print(f"Schema info: {schema_info}")

    logger.info("Server tests completed")


if __name__ == "__main__":
    # Allow direct testing
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        asyncio.run(test_server())
    else:
        asyncio.run(run_server())
