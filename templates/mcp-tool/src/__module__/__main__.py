"""{{TOOL_HYPHEN}} MCP Server entry point.

Run:
  uvx python -m {{TOOL_MODULE}}              # start server (stdio, awaits MCP client)
  uvx python -m {{TOOL_MODULE}} --test       # run internal self-tests then exit
"""

import argparse
import asyncio
import sys

from {{TOOL_MODULE}}.server import run_server, test_server


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI arguments for the {{TOOL_HYPHEN}} server entrypoint."""
    parser = argparse.ArgumentParser(prog="{{TOOL_MODULE}}", add_help=True)
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run built-in server self tests then exit.",
    )
    return parser.parse_args(argv)


def main() -> None:
    """CLI dispatcher for {{TOOL_HYPHEN}} MCP Server."""
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
        sys.exit(1)


if __name__ == "__main__":
    main()
