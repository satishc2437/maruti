"""
MCP Server setup and registration for PDF Reader.

Handles server initialization, tool registration, resource setup,
and JSON-RPC communication over stdio.
"""

import asyncio
import json
import sys
import logging
from typing import Any, Dict, List

# MCP imports
try:
    from mcp.server import Server
    from mcp.types import Tool, Resource, TextContent
except ImportError:
    raise ImportError("MCP library not installed. Install with: pip install mcp")

from .tools import (
    TOOL_METADATA,
    tool_extract_pdf_content,
    tool_get_pdf_metadata, 
    tool_list_pdf_pages,
    tool_stream_pdf_extraction
)
from .safety import check_ocr_available

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

# Create MCP server instance
server = Server("pdf-reader")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available PDF processing tools."""
    tools = []
    
    for tool_name, metadata in TOOL_METADATA.items():
        tool = Tool(
            name=tool_name,
            description=metadata["description"],
            inputSchema=metadata["inputSchema"]
        )
        tools.append(tool)
    
    logger.info(f"Listed {len(tools)} PDF processing tools")
    return tools


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """
    Handle tool execution requests and ensure MCP-compliant response format.

    Always returns list[TextContent] so that the MCP client never receives
    raw dicts (which caused previous Pydantic validation errors complaining
    about missing 'type' / 'text' fields for CallToolResult.content[0]).
    """
    if not isinstance(arguments, dict):
        arguments = {}

    logger.info(f"Tool called: {name} args={json.dumps(arguments, default=str)}")

    try:
        # Dispatch to tool implementations
        if name == "extract_pdf_content":
            raw_result = await tool_extract_pdf_content(arguments)
        elif name == "get_pdf_metadata":
            raw_result = await tool_get_pdf_metadata(arguments)
        elif name == "list_pdf_pages":
            raw_result = await tool_list_pdf_pages(arguments)
        elif name == "stream_pdf_extraction":
            # Streaming not supported via plain call_tool path
            raw_result = {
                "ok": False,
                "code": "UserInput",
                "message": "Streaming tool not supported in direct call mode",
                "hint": "Use an MCP client with streaming support for 'stream_pdf_extraction'"
            }
        else:
            raw_result = {
                "ok": False,
                "code": "UserInput",
                "message": f"Unknown tool: {name}",
                "hint": f"Available tools: {', '.join(TOOL_METADATA.keys())}"
            }

        # Defensive normalization: if a tool accidentally returns a plain list or scalar
        # wrap it in a success envelope so JSON dump is always structured.
        if not isinstance(raw_result, dict) or ("ok" not in raw_result):
            raw_result = {"ok": True, "data": raw_result}

        logger.info(f"Tool {name} completed ok={raw_result.get('ok')} code={raw_result.get('code','')}")

        # Always serialize tool result as JSON string inside TextContent
        content = TextContent(type="text", text=json.dumps(raw_result, indent=2, default=str))
        return [content]

    except Exception as e:
        logger.error(f"Tool {name} failed with unexpected exception: {e}")
        error_result = {
            "ok": False,
            "code": "Internal",
            "message": "Tool execution failed",
            "detail": str(e)
        }
        content = TextContent(type="text", text=json.dumps(error_result, indent=2, default=str))
        return [content]


@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources."""
    resources = [
        Resource(
            uri="pdf://supported-features",
            name="Supported PDF Features",
            description="Information about supported PDF processing capabilities"
        ),
        Resource(
            uri="pdf://server-status",
            name="Server Status",
            description="Current server status and configuration"
        )
    ]
    
    logger.info(f"Listed {len(resources)} resources")
    return resources


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read resource content."""
    logger.info(f"Resource requested: {uri}")
    
    if uri == "pdf://supported-features":
        features = {
            "text_extraction": True,
            "image_extraction": True,
            "table_extraction": True,
            "metadata_extraction": True,
            "ocr_support": False,
            "streaming_support": True,
            "supported_formats": [".pdf"],
            "max_file_size_mb": 100,
            "dependencies": {
                "PyPDF2": "Basic PDF reading",
                "pdfplumber": "Advanced text and table extraction",
                "Pillow": "Image processing",
                "pandas": "Table data processing"
            },
            "limitations": [
                "Password-protected PDFs not supported",
                "Very large files (>100MB) may timeout",
                "OCR functionality not available",
                "Complex table layouts may not extract perfectly"
            ]
        }
        return json.dumps(features, indent=2)
    
    elif uri == "pdf://server-status":
        status = {
            "server_name": "PDF Reader MCP Server",
            "version": "1.0.0",
            "tools_available": len(TOOL_METADATA),
            "tool_names": list(TOOL_METADATA.keys()),
            "ocr_available": False,
            "max_file_size_mb": 100,
            "safety_features": [
                "File size limits",
                "Path traversal protection",
                "File type validation",
                "Timeout protection"
            ]
        }
        return json.dumps(status, indent=2)
    
    else:
        raise ValueError(f"Unknown resource URI: {uri}")


async def run_server():
    """Run the PDF Reader MCP Server."""
    logger.info("Starting PDF Reader MCP Server...")
    
    # Check dependencies
    try:
        import PyPDF2
        import pdfplumber
        from PIL import Image
        logger.info("Core PDF processing libraries loaded successfully")
    except ImportError as e:
        logger.error(f"Missing required dependency: {e}")
        logger.error("Install dependencies with: pip install -r requirements.txt")
        sys.exit(1)
    
    # Check OCR availability
    ocr_status = "available" if check_ocr_available() else "not available"
    logger.info(f"OCR support: {ocr_status}")
    
    # Log available tools
    logger.info(f"Registered tools: {', '.join(TOOL_METADATA.keys())}")
    
    try:
        # Run server with stdio transport
        from mcp.server.stdio import stdio_server
        
        logger.info("PDF Reader MCP Server ready for connections")
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
            
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


# For direct testing
async def test_server():
    """Simple test function for development."""
    logger.info("Running server tests...")
    
    # Test tool listing
    tools = await list_tools()
    print(f"Available tools: {[t.name for t in tools]}")
    
    # Test resource listing
    resources = await list_resources()
    print(f"Available resources: {[r.name for r in resources]}")
    
    # Test resource reading
    status = await read_resource("pdf://server-status")
    print(f"Server status: {status}")
    
    logger.info("Server tests completed")


if __name__ == "__main__":
    # Allow direct testing
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        asyncio.run(test_server())
    else:
        asyncio.run(run_server())