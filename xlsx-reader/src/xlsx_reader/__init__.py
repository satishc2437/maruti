"""
Excel Reader MCP Server

A comprehensive MCP server for reading and editing Microsoft Excel (.xlsx) workbooks.
Provides tools for data extraction, manipulation, chart processing, and export capabilities.
"""

__version__ = "0.1.0"
__author__ = "MCP Generator"

from .server import run

__all__ = ["run"]
