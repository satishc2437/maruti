#!/usr/bin/env python3
"""
PDF Reader MCP Server Entry Point

Run:
  uvx python -m pdf_reader                # start server (stdio, waits for MCP client)
  uvx python -m pdf_reader --test         # run internal self-tests then exit
"""

import asyncio
import sys
import argparse
from pdf_reader.server import run_server, test_server


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="pdf_reader", add_help=True)
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run built-in server self tests (tool & resource listing) then exit."
    )
    return parser.parse_args(argv)


def main():
    """CLI dispatcher for PDF Reader MCP Server."""
    args = parse_args(sys.argv[1:])
    try:
        if args.test:
            # Run lightweight self-test (does NOT start persistent server loop)
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