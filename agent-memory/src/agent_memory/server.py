"""
Agent Memory MCP server (stdio JSON-RPC skeleton).
Registers tools and serves requests deterministically.
"""
from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, Awaitable, Callable, Dict

TIMEOUT_SECONDS: float = 3.0

# Minimal error helpers (will be replaced by errors.py later)
def _ok(result: Any) -> Dict[str, Any]:
    """Wrap successful tool output in a deterministic envelope."""
    return {"ok": True, **(result if isinstance(result, dict) else {"result": result})}

def _err(code: str, message: str, hint: str | None = None) -> Dict[str, Any]:
    """Create a standardized error payload."""
    out: Dict[str, Any] = {"ok": False, "code": code, "message": message}
    if hint:
        out["hint"] = hint
    return out

# Tool function type
ToolFunc = Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]

TOOLS: Dict[str, ToolFunc] = {}

# Import tool handlers
try:
    from .tools import (append_entry, list_sessions, read_summary,
                        start_session, update_summary)
except ImportError:
    # Tools may not be available during very early scaffold; keep server bootable
    start_session = append_entry = read_summary = update_summary = list_sessions = None  # type: ignore

async def _readline() -> str:
    """Read one line from stdin as text using a thread to avoid blocking the event loop."""
    line = await asyncio.to_thread(sys.stdin.readline)
    return line.rstrip("\n")

def _write_json(obj: Dict[str, Any]) -> None:
    """Write one JSON object line to stdout deterministically."""
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()

async def run() -> None:
    """
    Start JSON-RPC over stdio. Accepts one-line JSON requests.
    Protocol:
      {"jsonrpc":"2.0","id":"<id>","method":"tool_call","params":{"name":"<tool>","arguments":{...}}}
    """
    # Register tools deterministically
    TOOLS.clear()
    if start_session:
        TOOLS["start_session"] = start_session  # Create/open session file
    if append_entry:
        TOOLS["append_entry"] = append_entry    # Append to section in session log
    if read_summary:
        TOOLS["read_summary"] = read_summary    # Read _summary.md
    if update_summary:
        TOOLS["update_summary"] = update_summary  # Update section in _summary.md
    if list_sessions:
        TOOLS["list_sessions"] = list_sessions  # List YYYY-MM-DD.md files newest->oldest

    # Minimal health check tool
    async def ping(_params: Dict[str, Any]) -> Dict[str, Any]:
        return _ok({"pong": True, "version": "1.0.0"})
    TOOLS["ping"] = ping

    try:
        while True:
            line_str = await _readline()
            if not line_str:
                break
            if not line_str.strip():
                continue
            try:
                req = json.loads(line_str)
            except json.JSONDecodeError:
                _write_json({"jsonrpc": "2.0", "id": None, "error": _err("UserInput", "Malformed JSON")})
                continue

            rid = req.get("id")
            method = req.get("method")
            params: Dict[str, Any] = req.get("params") or {}

            if method != "tool_call":
                _write_json({"jsonrpc": "2.0", "id": rid, "error": _err("UserInput", "Unknown method", hint="Use method 'tool_call'")})
                continue

            name_raw = params.get("name")
            if not isinstance(name_raw, str):
                _write_json({"jsonrpc": "2.0", "id": rid, "error": _err("UserInput", "Tool name must be string")})
                continue
            name: str = name_raw
            arguments: Dict[str, Any] = params.get("arguments") or {}
            tool = TOOLS.get(name)
            if tool is None:
                _write_json({"jsonrpc": "2.0", "id": rid, "error": _err("NotFound", f"Tool '{name}' not registered")})
                continue

            try:
                result = await asyncio.wait_for(tool(arguments), timeout=TIMEOUT_SECONDS)
                _write_json({"jsonrpc": "2.0", "id": rid, "result": result})
            except asyncio.TimeoutError:
                _write_json({"jsonrpc": "2.0", "id": rid, "error": _err("Timeout", f"Operation exceeded {TIMEOUT_SECONDS:.1f}s limit")})
            except Exception as exc:  # pylint: disable=broad-except
                _write_json({"jsonrpc": "2.0", "id": rid, "error": _err("Internal", "Unhandled server error")})
                # Best effort structured log to stderr without raising
                try:
                    loop = asyncio.get_running_loop()
                    sys.stderr.write(json.dumps({"ts": loop.time(), "event": "error", "detail": str(exc)}) + "\n")
                except Exception:  # pylint: disable=broad-except
                    pass
    finally:
        # Finalize writer flush without raising
        try:
            sys.stdout.flush()
        except Exception:  # pylint: disable=broad-except
            pass
