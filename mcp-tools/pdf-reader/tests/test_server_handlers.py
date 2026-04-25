"""Behavior tests for pdf_reader.server MCP handlers and dispatch.

Exercises the registered MCP server handlers (list_tools, call_tool,
list_resources, read_resource) directly, plus run_server's dependency
check / startup paths and the bundled self-test helper.
"""

import json
import sys
from unittest.mock import AsyncMock, patch

import pytest
from mcp.types import TextContent

from pdf_reader.server import (
    call_tool,
    list_resources,
    list_tools,
    read_resource,
    run_server,
)
# Import dev self-test under an alias so pytest does not collect it as a test.
from pdf_reader.server import test_server as run_self_test


# ---------------------------------------------------------------------------
# Tool listing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_tools_returns_full_metadata_set():
    """list_tools exposes every PDF tool with description+schema."""
    tools = await list_tools()
    names = {t.name for t in tools}
    expected = {
        "extract_pdf_content",
        "get_pdf_metadata",
        "list_pdf_pages",
        "stream_pdf_extraction",
    }
    assert expected <= names
    for tool in tools:
        assert tool.description
        assert tool.inputSchema


# ---------------------------------------------------------------------------
# call_tool: per-tool routing
# ---------------------------------------------------------------------------


def _envelope(result):
    """Decode the JSON envelope embedded in a TextContent response."""
    assert isinstance(result, list) and len(result) == 1
    assert isinstance(result[0], TextContent)
    return json.loads(result[0].text)


@pytest.mark.asyncio
async def test_call_tool_extract_pdf_content_routes_to_extract_handler():
    """extract_pdf_content via call_tool reaches its tool function."""
    sentinel = {"ok": True, "data": {"pages": []}}
    with patch(
        "pdf_reader.server.tool_extract_pdf_content",
        new=AsyncMock(return_value=sentinel),
    ) as handler:
        result = await call_tool("extract_pdf_content", {"file_path": "x.pdf"})
    handler.assert_awaited_once()
    assert _envelope(result) == sentinel


@pytest.mark.asyncio
async def test_call_tool_get_pdf_metadata_routes_to_metadata_handler():
    """get_pdf_metadata via call_tool reaches its tool function."""
    sentinel = {"ok": True, "data": {"page_count": 3}}
    with patch(
        "pdf_reader.server.tool_get_pdf_metadata",
        new=AsyncMock(return_value=sentinel),
    ) as handler:
        result = await call_tool("get_pdf_metadata", {"file_path": "x.pdf"})
    handler.assert_awaited_once()
    assert _envelope(result) == sentinel


@pytest.mark.asyncio
async def test_call_tool_list_pdf_pages_routes_to_pages_handler():
    """list_pdf_pages via call_tool reaches its tool function."""
    sentinel = {"ok": True, "data": []}
    with patch(
        "pdf_reader.server.tool_list_pdf_pages",
        new=AsyncMock(return_value=sentinel),
    ) as handler:
        result = await call_tool("list_pdf_pages", {"file_path": "x.pdf"})
    handler.assert_awaited_once()
    assert _envelope(result) == sentinel


@pytest.mark.asyncio
async def test_call_tool_stream_pdf_extraction_returns_user_input_redirect():
    """Streaming extraction in plain call mode returns a UserInput redirect."""
    payload = _envelope(await call_tool("stream_pdf_extraction", {"file_path": "x.pdf"}))
    assert payload["ok"] is False
    assert payload["code"] == "UserInput"
    assert "streaming" in payload["hint"].lower()


# ---------------------------------------------------------------------------
# call_tool: error & defensive paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_tool_unknown_name_returns_user_input_error():
    """Unknown tool names return a UserInput error envelope."""
    payload = _envelope(await call_tool("nonexistent_tool", {}))
    assert payload["ok"] is False
    assert payload["code"] == "UserInput"
    assert "Unknown tool" in payload["message"]


@pytest.mark.asyncio
async def test_call_tool_non_dict_arguments_coerced_to_empty_dict():
    """Non-dict arguments are coerced to {} rather than raising."""
    payload = _envelope(await call_tool("nonexistent_tool", "not-a-dict"))  # type: ignore[arg-type]
    assert payload["ok"] is False
    assert payload["code"] == "UserInput"


@pytest.mark.asyncio
async def test_call_tool_unexpected_exception_returns_internal_error_envelope():
    """An unhandled exception is caught and reported as Internal."""
    with patch(
        "pdf_reader.server.tool_get_pdf_metadata",
        new=AsyncMock(side_effect=RuntimeError("boom")),
    ):
        payload = _envelope(await call_tool("get_pdf_metadata", {}))
    assert payload["ok"] is False
    assert payload["code"] == "Internal"
    assert "boom" in payload["detail"]


@pytest.mark.asyncio
async def test_call_tool_non_envelope_result_normalized_to_envelope():
    """When a tool returns a bare value, server wraps it as {ok, data}."""
    with patch(
        "pdf_reader.server.tool_get_pdf_metadata",
        new=AsyncMock(return_value=["a", "b"]),
    ):
        payload = _envelope(await call_tool("get_pdf_metadata", {}))
    assert payload["ok"] is True
    assert payload["data"] == ["a", "b"]


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_resources_returns_two_known_uris():
    """list_resources surfaces supported-features and server-status."""
    resources = await list_resources()
    uris = {str(r.uri) for r in resources}
    assert uris == {"pdf://supported-features", "pdf://server-status"}


@pytest.mark.asyncio
async def test_read_resource_supported_features_returns_capability_payload():
    """supported-features resource exposes capability flags and limits."""
    payload = json.loads(await read_resource("pdf://supported-features"))
    assert payload["text_extraction"] is True
    assert payload["max_file_size_mb"] == 100
    assert ".pdf" in payload["supported_formats"]


@pytest.mark.asyncio
async def test_read_resource_server_status_returns_metadata():
    """server-status resource includes name, version, tool inventory."""
    payload = json.loads(await read_resource("pdf://server-status"))
    assert payload["server_name"] == "PDF Reader MCP Server"
    assert payload["tools_available"] >= 1
    assert isinstance(payload["tool_names"], list)


@pytest.mark.asyncio
async def test_read_resource_unknown_uri_raises_value_error():
    """Unknown resource URIs raise ValueError with the offending URI."""
    with pytest.raises(ValueError, match="Unknown resource URI"):
        await read_resource("pdf://does-not-exist")


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
         patch("pdf_reader.server.server.run", new=AsyncMock()) as mock_run:
        await run_server()
    mock_run.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_server_swallows_keyboard_interrupt():
    """run_server logs and returns cleanly on KeyboardInterrupt — no re-raise."""
    with patch("mcp.server.stdio.stdio_server", return_value=_FakeStdioCtx()), \
         patch(
             "pdf_reader.server.server.run",
             new=AsyncMock(side_effect=KeyboardInterrupt()),
         ):
        await run_server()  # should not raise


@pytest.mark.asyncio
async def test_run_server_reraises_unexpected_exception():
    """run_server re-raises non-KeyboardInterrupt exceptions after logging."""
    with patch("mcp.server.stdio.stdio_server", return_value=_FakeStdioCtx()), \
         patch(
             "pdf_reader.server.server.run",
             new=AsyncMock(side_effect=RuntimeError("network-down")),
         ):
        with pytest.raises(RuntimeError, match="network-down"):
            await run_server()


@pytest.mark.asyncio
async def test_run_server_exits_when_pdf_dependency_missing(monkeypatch):
    """If the bundled dependency probe fails, run_server calls sys.exit(1)."""
    # The probe imports pypdf inside run_server. Force it to fail.
    real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pypdf":
            raise ImportError("simulated-missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    with pytest.raises(SystemExit) as exc_info:
        await run_server()
    assert exc_info.value.code == 1


@pytest.mark.asyncio
async def test_self_test_smoke_lists_tools_resources_and_status(capsys):
    """The bundled self-test prints discovered tools, resources, and status."""
    await run_self_test()
    captured = capsys.readouterr()
    assert "Available tools" in captured.out
    assert "Available resources" in captured.out
    assert "Server status" in captured.out
