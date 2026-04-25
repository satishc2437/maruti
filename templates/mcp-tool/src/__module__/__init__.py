"""{{TOOL_HYPHEN}} MCP server package.

{{TOOL_DESCRIPTION}}
"""

__version__ = "0.1.0"

try:
    from .server import run_server, test_server  # noqa: F401

    __all__ = ["run_server", "test_server"]
except ImportError:
    __all__ = []
