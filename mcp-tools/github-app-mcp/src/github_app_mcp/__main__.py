#!/usr/bin/env python3
"""github-app-mcp MCP Server entry point.

Run:
  uvx python -m github_app_mcp                # start server (stdio)
  uvx python -m github_app_mcp --test         # run lightweight self-tests then exit
"""

import argparse
import asyncio
import sys

from github_app_mcp.server import run_server, test_server


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(prog="github_app_mcp", add_help=True)
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run built-in server self tests (tool & resource listing) then exit.",
    )
    return parser.parse_args(argv)


def main() -> None:
    """CLI dispatcher for the MCP server."""
    args = parse_args(sys.argv[1:])
    try:
        if args.test:
            asyncio.run(test_server())
        else:
            asyncio.run(run_server())
    except KeyboardInterrupt:
        print("\nServer stopped by user", file=sys.stderr)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"Server error: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
