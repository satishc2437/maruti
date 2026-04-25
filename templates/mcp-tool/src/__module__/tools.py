"""Tool definitions and dispatch for {{TOOL_HYPHEN}}.

Replace the example_tool entry below with your real tools. Each tool
function should:
- accept a single ``arguments`` dict
- return a dict envelope of the form ``{"ok": True, "data": ...}`` or
  ``{"ok": False, "code": "...", "message": "...", "hint": "..."}``
"""

from typing import Any, Dict


TOOL_METADATA: Dict[str, Dict[str, Any]] = {
    "example_tool": {
        "description": "Placeholder example tool; replace with real tools.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "echo": {
                    "type": "string",
                    "description": "Text to echo back unchanged.",
                }
            },
            "required": ["echo"],
        },
    },
}


async def tool_example_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Echo back the ``echo`` argument unchanged."""
    text = arguments.get("echo")
    if not isinstance(text, str):
        return {
            "ok": False,
            "code": "UserInput",
            "message": "Parameter 'echo' must be a string.",
        }
    return {"ok": True, "data": {"echoed": text}}
