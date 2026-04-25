"""Behavior tests for agent_memory.server MCP handlers and dispatch.

Exercises the registered MCP server handlers (list_tools, call_tool,
list_resources, read_resource) directly by importing them from the server
module. Also covers the run_server / self-test dispatch paths by patching
the stdio transport.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from mcp.types import TextContent

from agent_memory.server import (
    call_tool,
    list_resources,
    list_tools,
    read_resource,
    run_server,
)
# Import dev self-test under an alias so pytest does not collect it as a test.
from agent_memory.server import test_server as run_self_test


# ---------------------------------------------------------------------------
# Tool listing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_tools_returns_full_metadata_set():
    """list_tools exposes all five agent-memory tools with description+schema."""
    tools = await list_tools()
    names = {t.name for t in tools}
    assert names == {
        "start_session",
        "append_entry",
        "read_summary",
        "update_summary",
        "list_sessions",
    }
    for tool in tools:
        assert tool.description
        assert tool.inputSchema


# ---------------------------------------------------------------------------
# call_tool: routing for each registered tool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_tool_start_session_happy_path(tmp_path):
    """start_session via call_tool returns a JSON success envelope."""
    result = await call_tool(
        "start_session",
        {"agent_name": "test_agent", "repo_root": str(tmp_path)},
    )
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    payload = json.loads(result[0].text)
    assert payload["ok"] is True


@pytest.mark.asyncio
async def test_call_tool_append_entry_happy_path(tmp_path):
    """append_entry via call_tool succeeds for a valid section."""
    result = await call_tool(
        "append_entry",
        {
            "agent_name": "test_agent",
            "repo_root": str(tmp_path),
            "section": "Context",
            "content": "first entry",
        },
    )
    payload = json.loads(result[0].text)
    assert payload["ok"] is True


@pytest.mark.asyncio
async def test_call_tool_read_summary_happy_path(tmp_path):
    """read_summary via call_tool returns the summary envelope."""
    result = await call_tool(
        "read_summary",
        {"agent_name": "test_agent", "repo_root": str(tmp_path)},
    )
    payload = json.loads(result[0].text)
    assert payload["ok"] is True


@pytest.mark.asyncio
async def test_call_tool_update_summary_happy_path(tmp_path):
    """update_summary via call_tool succeeds with append mode."""
    result = await call_tool(
        "update_summary",
        {
            "agent_name": "test_agent",
            "repo_root": str(tmp_path),
            "section": "Overview",
            "content": "summary content",
            "mode": "append",
        },
    )
    payload = json.loads(result[0].text)
    assert payload["ok"] is True


@pytest.mark.asyncio
async def test_call_tool_list_sessions_happy_path(tmp_path):
    """list_sessions via call_tool returns the sessions envelope."""
    result = await call_tool(
        "list_sessions",
        {"agent_name": "test_agent", "repo_root": str(tmp_path)},
    )
    payload = json.loads(result[0].text)
    assert payload["ok"] is True


# ---------------------------------------------------------------------------
# call_tool: error & defensive paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_tool_unknown_name_returns_user_input_error():
    """Unknown tool names return a structured UserInput error envelope."""
    result = await call_tool("nonexistent_tool", {})
    payload = json.loads(result[0].text)
    assert payload["ok"] is False
    assert payload["code"] == "UserInput"
    assert "Unknown tool" in payload["message"]


@pytest.mark.asyncio
async def test_call_tool_non_dict_arguments_coerced_to_empty_dict():
    """Non-dict arguments are coerced to {} rather than raising."""
    result = await call_tool("nonexistent_tool", "not-a-dict")  # type: ignore[arg-type]
    payload = json.loads(result[0].text)
    # Routes to unknown-tool path (not a TypeError on .get).
    assert payload["ok"] is False
    assert payload["code"] == "UserInput"


@pytest.mark.asyncio
async def test_call_tool_unexpected_exception_returns_internal_error_envelope():
    """An unhandled exception inside a tool is caught and reported as Internal."""
    with patch(
        "agent_memory.server.tool_start_session",
        new=AsyncMock(side_effect=RuntimeError("boom")),
    ):
        result = await call_tool("start_session", {})
    payload = json.loads(result[0].text)
    assert payload["ok"] is False
    assert payload["code"] == "Internal"
    assert "boom" in payload["detail"]


@pytest.mark.asyncio
async def test_call_tool_non_envelope_result_normalized_to_envelope():
    """When a tool returns a non-envelope value, server wraps it as {ok, data}."""
    with patch(
        "agent_memory.server.tool_start_session",
        new=AsyncMock(return_value=["a", "b"]),
    ):
        result = await call_tool("start_session", {})
    payload = json.loads(result[0].text)
    assert payload["ok"] is True
    assert payload["data"] == ["a", "b"]


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_resources_returns_three_known_uris():
    """list_resources surfaces schema-info, server-status, and usage-examples."""
    resources = await list_resources()
    uris = {str(r.uri) for r in resources}
    assert uris == {
        "memory://schema-info",
        "memory://server-status",
        "memory://usage-examples",
    }


@pytest.mark.asyncio
async def test_read_resource_schema_info_returns_structured_payload():
    """schema-info resource exposes schema_version, allowed sections, principles."""
    payload = json.loads(await read_resource("memory://schema-info"))
    assert "schema_version" in payload
    assert "allowed_sections" in payload
    assert isinstance(payload["allowed_sections"], list)
    assert payload["design_principles"]


@pytest.mark.asyncio
async def test_read_resource_server_status_returns_metadata():
    """server-status resource includes name, version, and tool inventory."""
    payload = json.loads(await read_resource("memory://server-status"))
    assert payload["server_name"] == "Agent Memory MCP Server"
    assert payload["tools_available"] >= 1
    assert "start_session" in payload["tool_names"]


@pytest.mark.asyncio
async def test_read_resource_usage_examples_returns_workflow_and_examples():
    """usage-examples resource exposes typical_workflow and per-tool examples."""
    payload = json.loads(await read_resource("memory://usage-examples"))
    assert payload["typical_workflow"]
    assert "start_session_example" in payload
    assert "append_entry_example" in payload


@pytest.mark.asyncio
async def test_read_resource_unknown_uri_raises_value_error():
    """Unknown resource URIs raise ValueError with the offending URI in the message."""
    with pytest.raises(ValueError, match="Unknown resource URI"):
        await read_resource("memory://does-not-exist")


# ---------------------------------------------------------------------------
# run_server / dev self-test
# ---------------------------------------------------------------------------


class _FakeStdioCtx:
    """Async context manager that yields a fake (read_stream, write_stream)."""

    async def __aenter__(self):
        """Return a fake pair of streams."""
        return (object(), object())

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Suppress nothing."""
        return False


@pytest.mark.asyncio
async def test_run_server_drives_server_run_inside_stdio_context():
    """run_server enters stdio_server and awaits server.run exactly once."""
    with patch("mcp.server.stdio.stdio_server", return_value=_FakeStdioCtx()), \
         patch("agent_memory.server.server.run", new=AsyncMock()) as mock_run:
        await run_server()
    mock_run.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_server_swallows_keyboard_interrupt():
    """run_server logs and returns cleanly on KeyboardInterrupt — no re-raise."""
    with patch("mcp.server.stdio.stdio_server", return_value=_FakeStdioCtx()), \
         patch(
             "agent_memory.server.server.run",
             new=AsyncMock(side_effect=KeyboardInterrupt()),
         ):
        await run_server()  # should not raise


@pytest.mark.asyncio
async def test_run_server_reraises_unexpected_exception():
    """run_server logs and re-raises unexpected exceptions."""
    with patch("mcp.server.stdio.stdio_server", return_value=_FakeStdioCtx()), \
         patch(
             "agent_memory.server.server.run",
             new=AsyncMock(side_effect=RuntimeError("network-down")),
         ):
        with pytest.raises(RuntimeError, match="network-down"):
            await run_server()


@pytest.mark.asyncio
async def test_self_test_smoke_lists_tools_resources_and_status(capsys):
    """The bundled self-test prints discovered tools, resources, and status."""
    await run_self_test()
    captured = capsys.readouterr()
    assert "Available tools" in captured.out
    assert "Available resources" in captured.out
    assert "Server status" in captured.out
