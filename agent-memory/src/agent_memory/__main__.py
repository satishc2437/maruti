#!/usr/bin/env python3
"""
Agent Memory MCP Server entrypoint.

Run:
  uvx python -m agent_memory
"""
import asyncio
import sys
from typing import NoReturn


def main() -> int:
    """Run the MCP server and return POSIX exit code."""
    try:
        # Import inside function to reduce import-time side effects for linters
        from agent_memory.server import run  # type: ignore
    except ImportError as exc:
        sys.stderr.write(f"Failed to import server: {exc}\n")
        return 1
    try:
        asyncio.run(run())
        return 0
    except KeyboardInterrupt:
        # Graceful shutdown
        return 0
    except Exception as exc:  # pylint: disable=broad-except
        sys.stderr.write(f"Server runtime error: {exc}\n")
        return 1


def _start() -> NoReturn:
    """Invoke main() and exit with its return code."""
    raise SystemExit(main())


if __name__ == "__main__":
    _start()
