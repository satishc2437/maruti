"""MCP server implementation for Excel Reader.

Provides comprehensive Excel workbook reading and editing capabilities.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# MCP imports
try:
    from mcp.server import Server
    from mcp.types import Resource, TextContent, Tool
except ImportError:
    raise ImportError("MCP library not installed. Install with: pip install mcp")

from .errors import (
    forbidden_error,
    internal_error,
    not_found_error,
    success_response,
    timeout_error,
    user_input_error,
)
from .processors.workbook import ExcelProcessor
from .safety import FileOperationContext

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

# Create MCP server instance
server = Server("xlsx-reader")

# Global processor instance
excel_processor = ExcelProcessor()


@server.list_resources()
async def handle_list_resources() -> List[Resource]:
    """List available resources."""
    return [
        Resource(
            uri="xlsx://supported-formats",
            name="Supported Excel Formats",
            description="List of supported Excel file formats and extensions",
            mimeType="application/json",
        ),
        Resource(
            uri="xlsx://server-status",
            name="Server Status",
            description="Current server status and loaded workbook information",
            mimeType="application/json",
        ),
    ]


@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Handle resource reading requests."""
    logger.info(f"Resource requested: {uri}")

    if uri == "xlsx://supported-formats":
        formats = {
            "supported_extensions": [".xlsx", ".xlsm", ".xltx", ".xltm"],
            "descriptions": {
                ".xlsx": "Excel Workbook (OpenXML format)",
                ".xlsm": "Excel Macro-Enabled Workbook",
                ".xltx": "Excel Template",
                ".xltm": "Excel Macro-Enabled Template",
            },
            "max_file_size_mb": 200,
            "capabilities": [
                "Read workbook metadata",
                "Read/write worksheet data",
                "Extract/modify charts",
                "Extract/modify pivot tables",
                "Cell formatting",
                "Data validation",
                "Export to CSV/JSON",
            ],
        }
        return json.dumps(formats, indent=2)

    elif uri == "xlsx://server-status":
        try:
            workbook_info = (
                excel_processor.get_workbook_info()
                if excel_processor._workbook
                else None
            )
        except Exception:
            workbook_info = None

        status = {
            "server": "xlsx-reader",
            "version": "1.0.0",
            "status": "running",
            "workbook_loaded": workbook_info is not None,
            "current_workbook": workbook_info,
        }
        return json.dumps(status, indent=2)

    else:
        raise ValueError(f"Unknown resource URI: {uri}")


@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools."""
    return [
        # Reading tools
        Tool(
            name="read_workbook_info",
            description="Read Excel workbook metadata and sheet information",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to Excel file",
                    },
                    "read_only": {
                        "type": "boolean",
                        "description": "Open in read-only mode",
                        "default": True,
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="read_worksheet_data",
            description="Read data from a specific worksheet",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to Excel file",
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Name of worksheet (active sheet if not specified)",
                    },
                    "include_formulas": {
                        "type": "boolean",
                        "description": "Include formula strings",
                        "default": False,
                    },
                    "cell_range": {
                        "type": "string",
                        "description": "Specific cell range (e.g., 'A1:D10')",
                    },
                },
                "required": ["file_path"],
            },
        ),
        # Editing tools
        Tool(
            name="update_cell_value",
            description="Update a single cell's value or formula",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to Excel file",
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Name of worksheet",
                    },
                    "cell_ref": {
                        "type": "string",
                        "description": "Cell reference (e.g., 'A1')",
                    },
                    "value": {
                        "type": ["string", "number", "boolean", "null"],
                        "description": "New cell value",
                    },
                    "formula": {
                        "type": "string",
                        "description": "Formula string (alternative to value)",
                    },
                },
                "required": ["file_path", "sheet_name", "cell_ref"],
            },
        ),
        Tool(
            name="update_cell_range",
            description="Update multiple cells in a range",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to Excel file",
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Name of worksheet",
                    },
                    "cell_range": {
                        "type": "string",
                        "description": "Cell range (e.g., 'A1:C3')",
                    },
                    "values": {
                        "type": "array",
                        "description": "2D array of values matching range dimensions",
                        "items": {
                            "type": "array",
                            "items": {"type": ["string", "number", "boolean", "null"]},
                        },
                    },
                },
                "required": ["file_path", "sheet_name", "cell_range", "values"],
            },
        ),
        # Worksheet management
        Tool(
            name="add_worksheet",
            description="Add a new worksheet to the workbook",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to Excel file",
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Name for new worksheet",
                    },
                    "index": {
                        "type": "integer",
                        "description": "Position to insert sheet (end if not specified)",
                    },
                },
                "required": ["file_path", "sheet_name"],
            },
        ),
        Tool(
            name="delete_worksheet",
            description="Delete a worksheet from the workbook",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to Excel file",
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Name of worksheet to delete",
                    },
                },
                "required": ["file_path", "sheet_name"],
            },
        ),
        # Export and save
        Tool(
            name="export_to_csv",
            description="Export worksheet data to CSV format",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to Excel file",
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Name of worksheet to export",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Path to save CSV file (optional)",
                    },
                    "include_headers": {
                        "type": "boolean",
                        "description": "Include first row as headers",
                        "default": True,
                    },
                },
                "required": ["file_path", "sheet_name"],
            },
        ),
        Tool(
            name="save_workbook",
            description="Save changes to the workbook",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Current Excel file path",
                    },
                    "save_as_path": {
                        "type": "string",
                        "description": "New path to save to (optional)",
                    },
                },
                "required": ["file_path"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool execution requests and ensure MCP-compliant response format.

    Always returns list[TextContent] so that the MCP client never receives
    raw dicts (which caused previous Pydantic validation errors).
    """
    if not isinstance(arguments, dict):
        arguments = {}

    logger.info(f"Tool called: {name} args={json.dumps(arguments, default=str)}")

    try:
        # Route to appropriate handler
        if name == "read_workbook_info":
            raw_result = await _read_workbook_info(arguments)
        elif name == "read_worksheet_data":
            raw_result = await _read_worksheet_data(arguments)
        elif name == "update_cell_value":
            raw_result = await _update_cell_value(arguments)
        elif name == "update_cell_range":
            raw_result = await _update_cell_range(arguments)
        elif name == "add_worksheet":
            raw_result = await _add_worksheet(arguments)
        elif name == "delete_worksheet":
            raw_result = await _delete_worksheet(arguments)
        elif name == "export_to_csv":
            raw_result = await _export_to_csv(arguments)
        elif name == "save_workbook":
            raw_result = await _save_workbook(arguments)
        else:
            raw_result = user_input_error(f"Unknown tool: {name}")

        # Defensive normalization: if a tool accidentally returns a plain list or scalar
        # wrap it in a success envelope so JSON dump is always structured.
        if not isinstance(raw_result, dict) or ("ok" not in raw_result):
            raw_result = {"ok": True, "data": raw_result}

        logger.info(
            f"Tool {name} completed ok={raw_result.get('ok')} code={raw_result.get('code', '')}"
        )

        # Always serialize tool result as JSON string inside TextContent
        content = TextContent(
            type="text", text=json.dumps(raw_result, indent=2, default=str)
        )
        return [content]

    except Exception as e:
        logger.error(f"Tool {name} failed with unexpected exception: {e}")
        error_result = {
            "ok": False,
            "code": "Internal",
            "message": "Tool execution failed",
            "detail": str(e),
        }
        content = TextContent(
            type="text", text=json.dumps(error_result, indent=2, default=str)
        )
        return [content]


# Tool implementation functions


async def _read_workbook_info(args: Dict[str, Any]) -> Dict[str, Any]:
    """Read workbook metadata and sheet information."""
    try:
        file_path = args.get("file_path")
        read_only = args.get("read_only", True)

        if not file_path:
            return user_input_error("Parameter 'file_path' is required")

        workbook_info = excel_processor.load_workbook(file_path, read_only=read_only)
        return success_response(workbook_info)

    except Exception as e:
        return internal_error("Failed to read workbook info", detail=str(e))


async def _read_worksheet_data(args: Dict[str, Any]) -> Dict[str, Any]:
    """Read data from a specific worksheet."""
    try:
        file_path = args.get("file_path")
        sheet_name = args.get("sheet_name")
        include_formulas = args.get("include_formulas", False)
        cell_range = args.get("cell_range")

        if not file_path:
            return user_input_error("Parameter 'file_path' is required")

        # Load workbook if not already loaded or different file
        if (
            not excel_processor._workbook
            or str(excel_processor._file_path) != file_path
        ):
            excel_processor.load_workbook(file_path, read_only=True)

        worksheet_data = excel_processor.get_worksheet_data(
            sheet_name=sheet_name,
            include_formulas=include_formulas,
            cell_range=cell_range,
        )

        return success_response(worksheet_data)

    except Exception as e:
        return internal_error("Failed to read worksheet data", detail=str(e))


async def _update_cell_value(args: Dict[str, Any]) -> Dict[str, Any]:
    """Update a single cell's value or formula."""
    try:
        file_path = args.get("file_path")
        sheet_name = args.get("sheet_name")
        cell_ref = args.get("cell_ref")
        value = args.get("value")
        formula = args.get("formula")

        if not all([file_path, sheet_name, cell_ref]):
            return user_input_error(
                "Parameters 'file_path', 'sheet_name', and 'cell_ref' are required"
            )

        if value is None and formula is None:
            return user_input_error("Either 'value' or 'formula' parameter is required")

        # Use file operation context for safety
        with FileOperationContext(file_path, create_backup=True):
            # Load workbook for editing
            if (
                not excel_processor._workbook
                or str(excel_processor._file_path) != file_path
            ):
                excel_processor.load_workbook(file_path, read_only=False)

            result = excel_processor.update_cell_value(
                sheet_name=sheet_name, cell_ref=cell_ref, value=value, formula=formula
            )

        return success_response(result)

    except Exception as e:
        return internal_error("Failed to update cell value", detail=str(e))


async def _update_cell_range(args: Dict[str, Any]) -> Dict[str, Any]:
    """Update multiple cells in a range."""
    try:
        file_path = args.get("file_path")
        sheet_name = args.get("sheet_name")
        cell_range = args.get("cell_range")
        values = args.get("values")

        if not all([file_path, sheet_name, cell_range, values]):
            return user_input_error(
                "Parameters 'file_path', 'sheet_name', 'cell_range', and 'values' are required"
            )

        if not isinstance(values, list):
            return user_input_error("Parameter 'values' must be a 2D array")

        with FileOperationContext(file_path, create_backup=True):
            if (
                not excel_processor._workbook
                or str(excel_processor._file_path) != file_path
            ):
                excel_processor.load_workbook(file_path, read_only=False)

            result = excel_processor.update_cell_range(
                sheet_name=sheet_name, cell_range=cell_range, values=values
            )

        return success_response(result)

    except Exception as e:
        return internal_error("Failed to update cell range", detail=str(e))


async def _add_worksheet(args: Dict[str, Any]) -> Dict[str, Any]:
    """Add a new worksheet to the workbook."""
    try:
        file_path = args.get("file_path")
        sheet_name = args.get("sheet_name")
        index = args.get("index")

        if not all([file_path, sheet_name]):
            return user_input_error(
                "Parameters 'file_path' and 'sheet_name' are required"
            )

        with FileOperationContext(file_path, create_backup=True):
            if (
                not excel_processor._workbook
                or str(excel_processor._file_path) != file_path
            ):
                excel_processor.load_workbook(file_path, read_only=False)

            result = excel_processor.add_worksheet(sheet_name=sheet_name, index=index)

        return success_response(result)

    except Exception as e:
        return internal_error("Failed to add worksheet", detail=str(e))


async def _delete_worksheet(args: Dict[str, Any]) -> Dict[str, Any]:
    """Delete a worksheet from the workbook."""
    try:
        file_path = args.get("file_path")
        sheet_name = args.get("sheet_name")

        if not all([file_path, sheet_name]):
            return user_input_error(
                "Parameters 'file_path' and 'sheet_name' are required"
            )

        with FileOperationContext(file_path, create_backup=True):
            if (
                not excel_processor._workbook
                or str(excel_processor._file_path) != file_path
            ):
                excel_processor.load_workbook(file_path, read_only=False)

            result = excel_processor.delete_worksheet(sheet_name=sheet_name)

        return success_response(result)

    except Exception as e:
        return internal_error("Failed to delete worksheet", detail=str(e))


async def _export_to_csv(args: Dict[str, Any]) -> Dict[str, Any]:
    """Export worksheet data to CSV format."""
    try:
        file_path = args.get("file_path")
        sheet_name = args.get("sheet_name")
        output_path = args.get("output_path")
        include_headers = args.get("include_headers", True)

        if not all([file_path, sheet_name]):
            return user_input_error(
                "Parameters 'file_path' and 'sheet_name' are required"
            )

        # Load workbook if needed
        if (
            not excel_processor._workbook
            or str(excel_processor._file_path) != file_path
        ):
            excel_processor.load_workbook(file_path, read_only=True)

        # Get worksheet data
        worksheet_data = excel_processor.get_worksheet_data(sheet_name=sheet_name)

        # Convert to CSV format
        import csv
        import io

        csv_content = io.StringIO()
        writer = csv.writer(csv_content)

        for row_data in worksheet_data["data"]:
            row_values = [cell["value"] for cell in row_data]
            writer.writerow(row_values)

        csv_string = csv_content.getvalue()
        csv_content.close()

        result = {
            "sheet_name": sheet_name,
            "rows_exported": len(worksheet_data["data"]),
            "csv_data": csv_string if not output_path else None,
        }

        # Save to file if output_path specified
        if output_path:
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                f.write(csv_string)
            result["saved_to"] = output_path
            result["file_size"] = len(csv_string.encode("utf-8"))

        return success_response(result)

    except Exception as e:
        return internal_error("Failed to export to CSV", detail=str(e))


async def _save_workbook(args: Dict[str, Any]) -> Dict[str, Any]:
    """Save changes to the workbook."""
    try:
        file_path = args.get("file_path")
        save_as_path = args.get("save_as_path")

        if not file_path:
            return user_input_error("Parameter 'file_path' is required")

        if not excel_processor._workbook:
            return user_input_error("No workbook is currently loaded")

        result = excel_processor.save_workbook(file_path=save_as_path or file_path)
        return success_response(result)

    except Exception as e:
        return internal_error("Failed to save workbook", detail=str(e))


async def run() -> None:
    """Run the MCP server."""
    logger.info("Starting Excel Reader MCP server")

    try:
        # Run server with stdio transport
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream, write_stream, server.create_initialization_options()
            )

    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        # Cleanup
        excel_processor.close_workbook()
        logger.info("Excel Reader MCP server stopped")
