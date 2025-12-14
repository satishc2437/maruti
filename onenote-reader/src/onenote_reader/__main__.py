#!/usr/bin/env python3
"""
OneNote MCP Server Entry Point

Current phase: Scaffold (Graph + OAuth not implemented yet).

Run:
  uvx python -m onenote_reader             # start stdio MCP server
  uvx python -m onenote_reader --test      # run lightweight self-test (no client)

Planned:
  * Device code auth (in-memory token)
  * Real Graph operations for read/write/list
"""

from __future__ import annotations

import sys
import argparse
import asyncio
from .server import run_server, test_server


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="onenote_reader", add_help=True)
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run internal self-tests (tool/resource listing) then exit."
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args(sys.argv[1:])
    try:
        if args.test:
            asyncio.run(test_server())
        else:
            asyncio.run(run_server())
    except KeyboardInterrupt:
        print("\nServer stopped by user", file=sys.stderr)
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()