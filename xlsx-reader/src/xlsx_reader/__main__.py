#!/usr/bin/env python3
"""
Entry point for the Excel Reader MCP server.

Run with:
  uvx python -m xlsx_reader
"""

import asyncio
import logging
import sys
from typing import Optional

from .server import run


def setup_logging(debug: bool = False) -> None:
    """Configure logging for the server."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )


def main() -> None:
    """Main entry point."""
    debug = "--debug" in sys.argv
    setup_logging(debug)

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logging.info("Server shutdown requested")
    except Exception as e:
        logging.error(f"Server failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
