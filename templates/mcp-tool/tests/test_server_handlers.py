"""Behavior tests for the {{TOOL_HYPHEN}} MCP server handlers."""

import json

import pytest
from mcp.types import TextContent

from {{TOOL_MODULE}}.server import call_tool, list_tools


def _envelope(result):
    """Decode the JSON envelope embedded in a TextContent response."""
    assert isinstance(result, list) and len(result) == 1
    assert isinstance(result[0], TextContent)
    return json.loads(result[0].text)


@pytest.mark.asyncio
async def test_list_tools_returns_example_tool():
    """list_tools surfaces the example_tool from TOOL_METADATA."""
    tools = await list_tools()
    names = {t.name for t in tools}
    assert "example_tool" in names


@pytest.mark.asyncio
async def test_call_tool_example_tool_echoes_string():
    """example_tool returns the echoed string in a success envelope."""
    payload = _envelope(await call_tool("example_tool", {"echo": "hello"}))
    assert payload["ok"] is True
    assert payload["data"]["echoed"] == "hello"


@pytest.mark.asyncio
async def test_call_tool_example_tool_rejects_non_string_echo():
    """example_tool returns UserInput when 'echo' is missing or not a string."""
    payload = _envelope(await call_tool("example_tool", {"echo": 123}))
    assert payload["ok"] is False
    assert payload["code"] == "UserInput"


@pytest.mark.asyncio
async def test_call_tool_unknown_name_returns_user_input_error():
    """Unknown tool names return a UserInput error envelope."""
    payload = _envelope(await call_tool("nonexistent_tool", {}))
    assert payload["ok"] is False
    assert payload["code"] == "UserInput"
