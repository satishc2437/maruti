"""Agent Memory MCP Server.

A deterministic Memory Control Plane for AI agents with structured,
versioned, repository-backed memory system.
"""

__version__ = "1.0.0"
__author__ = "MCP Generator"

# Conditional import to allow testing without MCP
try:
    from .server import run_server, test_server
    __all__ = ["run_server", "test_server"]
except ImportError:
    # MCP not available, skip server imports for testing
    __all__ = []
