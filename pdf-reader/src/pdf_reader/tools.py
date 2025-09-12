"""
PDF extraction tools for MCP server.

Implements tool adapters that wrap PDF processing logic with
validation, error handling, and MCP-compatible interfaces.
"""

import asyncio
from typing import Dict, Any, List, Optional
import logging

from .pdf_processor import PDFProcessor
from .safety import PDFSafetyError, FileSizeError, PathTraversalError, UnsupportedFileError
from .errors import (
    user_input_error, forbidden_error, not_found_error, 
    timeout_error, internal_error, cancellation_error
)

logger = logging.getLogger(__name__)

# Tool metadata for MCP registration
TOOL_METADATA = {
    "extract_pdf_content": {
        "description": "Extract comprehensive content from PDF including text, images, tables, and metadata",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the PDF file"
                },
                "pages": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Specific pages to extract (1-indexed). If not provided, extracts all pages."
                },
                "include_images": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to extract images from the PDF"
                },
                "include_tables": {
                    "type": "boolean", 
                    "default": True,
                    "description": "Whether to extract table structures"
                },
                "use_ocr": {
                    "type": "boolean",
                    "default": False,
                    "description": "OCR functionality not supported (parameter ignored)"
                }
            },
            "required": ["file_path"]
        }
    },
    "get_pdf_metadata": {
        "description": "Extract PDF metadata and document properties without processing content",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the PDF file"
                }
            },
            "required": ["file_path"]
        }
    },
    "list_pdf_pages": {
        "description": "Get a preview of PDF pages with text snippets for content overview",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the PDF file"
                },
                "start_page": {
                    "type": "integer",
                    "default": 1,
                    "minimum": 1,
                    "description": "Starting page number (1-indexed)"
                },
                "end_page": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Ending page number (1-indexed). If not provided, lists all pages from start_page."
                },
                "preview_length": {
                    "type": "integer",
                    "default": 200,
                    "minimum": 50,
                    "maximum": 1000,
                    "description": "Maximum characters per page preview"
                }
            },
            "required": ["file_path"]
        }
    },
    "stream_pdf_extraction": {
        "description": "Stream PDF content extraction with real-time progress updates for large documents",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the PDF file"
                },
                "pages": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Specific pages to extract (1-indexed). If not provided, extracts all pages."
                },
                "include_images": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to extract images from the PDF"
                },
                "include_tables": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to extract table structures"
                },
                "use_ocr": {
                    "type": "boolean",
                    "default": False,
                    "description": "OCR functionality not supported (parameter ignored)"
                }
            },
            "required": ["file_path"]
        }
    }
}

# Global PDF processor instance
pdf_processor = PDFProcessor()


def validate_extract_pdf_content_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Validate parameters for extract_pdf_content tool."""
    file_path = params.get("file_path")
    if not file_path or not isinstance(file_path, str):
        raise ValueError("Parameter 'file_path' is required and must be a string")
    
    pages = params.get("pages")
    if pages is not None:
        if not isinstance(pages, list) or not all(isinstance(p, int) and p > 0 for p in pages):
            raise ValueError("Parameter 'pages' must be a list of positive integers")
    
    include_images = params.get("include_images", True)
    if not isinstance(include_images, bool):
        raise ValueError("Parameter 'include_images' must be a boolean")
    
    include_tables = params.get("include_tables", True)
    if not isinstance(include_tables, bool):
        raise ValueError("Parameter 'include_tables' must be a boolean")
    
    use_ocr = params.get("use_ocr", False)
    if not isinstance(use_ocr, bool):
        raise ValueError("Parameter 'use_ocr' must be a boolean")
    
    # OCR functionality removed - always set to False
    return {
        "file_path": file_path,
        "pages": pages,
        "include_images": include_images,
        "include_tables": include_tables,
        "use_ocr": False  # OCR not supported
    }


def validate_metadata_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Validate parameters for get_pdf_metadata tool."""
    file_path = params.get("file_path")
    if not file_path or not isinstance(file_path, str):
        raise ValueError("Parameter 'file_path' is required and must be a string")
    
    return {"file_path": file_path}


def validate_list_pages_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Validate parameters for list_pdf_pages tool."""
    file_path = params.get("file_path")
    if not file_path or not isinstance(file_path, str):
        raise ValueError("Parameter 'file_path' is required and must be a string")
    
    start_page = params.get("start_page", 1)
    if not isinstance(start_page, int) or start_page < 1:
        raise ValueError("Parameter 'start_page' must be a positive integer")
    
    end_page = params.get("end_page")
    if end_page is not None and (not isinstance(end_page, int) or end_page < 1):
        raise ValueError("Parameter 'end_page' must be a positive integer")
    
    preview_length = params.get("preview_length", 200)
    if not isinstance(preview_length, int) or not (50 <= preview_length <= 1000):
        raise ValueError("Parameter 'preview_length' must be an integer between 50 and 1000")
    
    return {
        "file_path": file_path,
        "start_page": start_page,
        "end_page": end_page,
        "preview_length": preview_length
    }


async def run_with_timeout(coro, timeout_seconds: float = 30.0):
    """Run coroutine with timeout protection."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        return timeout_error(f"Operation exceeded {timeout_seconds:.1f}s limit")


async def tool_extract_pdf_content(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool: Extract comprehensive PDF content including text, images, tables, and metadata.
    """
    try:
        validated = validate_extract_pdf_content_params(params or {})
    except ValueError as e:
        return user_input_error(str(e), hint="Check parameter types and values")
    
    try:
        result = await run_with_timeout(
            pdf_processor.extract_full_content(
                validated["file_path"],
                validated["pages"],
                validated["include_images"],
                validated["include_tables"],
                validated["use_ocr"]
            ),
            timeout_seconds=60.0  # Longer timeout for full extraction
        )
        
        if isinstance(result, dict) and not result.get("ok", True):
            return result  # Already an error response
        
        return {"ok": True, "data": result}
        
    except PDFSafetyError as e:
        if isinstance(e, PathTraversalError):
            return forbidden_error(str(e))
        elif isinstance(e, FileSizeError):
            return user_input_error(str(e), hint="Use a smaller PDF file or process specific pages")
        elif isinstance(e, UnsupportedFileError):
            return user_input_error(str(e), hint="Ensure the file is a valid PDF")
        else:
            return forbidden_error(str(e))
    except FileNotFoundError as e:
        return not_found_error(str(e))
    except Exception as e:
        return internal_error("Failed to extract PDF content", detail=str(e))


async def tool_get_pdf_metadata(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool: Extract PDF metadata and document properties.
    """
    try:
        validated = validate_metadata_params(params or {})
    except ValueError as e:
        return user_input_error(str(e), hint="Provide a valid file_path string")
    
    try:
        result = await run_with_timeout(
            pdf_processor.extract_metadata(validated["file_path"]),
            timeout_seconds=10.0
        )
        
        if isinstance(result, dict) and not result.get("ok", True):
            return result  # Already an error response
        
        return {"ok": True, "data": result}
        
    except PDFSafetyError as e:
        if isinstance(e, PathTraversalError):
            return forbidden_error(str(e))
        elif isinstance(e, FileSizeError):
            return user_input_error(str(e), hint="File too large for processing")
        elif isinstance(e, UnsupportedFileError):
            return user_input_error(str(e), hint="Ensure the file is a valid PDF")
        else:
            return forbidden_error(str(e))
    except FileNotFoundError as e:
        return not_found_error(str(e))
    except Exception as e:
        return internal_error("Failed to extract PDF metadata", detail=str(e))


async def tool_list_pdf_pages(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool: Get preview of PDF pages with text snippets.
    """
    try:
        validated = validate_list_pages_params(params or {})
    except ValueError as e:
        return user_input_error(str(e), hint="Check parameter types and ranges")
    
    try:
        result = await run_with_timeout(
            pdf_processor.extract_page_text_preview(
                validated["file_path"],
                validated["start_page"],
                validated["end_page"],
                validated["preview_length"]
            ),
            timeout_seconds=20.0
        )
        
        if isinstance(result, dict) and not result.get("ok", True):
            return result  # Already an error response
        
        return {"ok": True, "data": result}
        
    except PDFSafetyError as e:
        if isinstance(e, PathTraversalError):
            return forbidden_error(str(e))
        elif isinstance(e, FileSizeError):
            return user_input_error(str(e), hint="File too large for processing")
        elif isinstance(e, UnsupportedFileError):
            return user_input_error(str(e), hint="Ensure the file is a valid PDF")
        else:
            return forbidden_error(str(e))
    except FileNotFoundError as e:
        return not_found_error(str(e))
    except Exception as e:
        return internal_error("Failed to list PDF pages", detail=str(e))


async def tool_stream_pdf_extraction(params: Dict[str, Any], send_event) -> Dict[str, Any]:
    """
    Streaming Tool: Extract PDF content with real-time progress updates.
    """
    try:
        validated = validate_extract_pdf_content_params(params or {})
    except ValueError as e:
        return user_input_error(str(e), hint="Check parameter types and values")
    
    try:
        result = await pdf_processor.stream_content_extraction(
            validated["file_path"],
            send_event,
            validated["pages"],
            validated["include_images"],
            validated["include_tables"],
            validated["use_ocr"]
        )
        
        return {"ok": True, "data": result}
        
    except PDFSafetyError as e:
        await send_event({"type": "error", "message": str(e)})
        if isinstance(e, PathTraversalError):
            return forbidden_error(str(e))
        elif isinstance(e, FileSizeError):
            return user_input_error(str(e), hint="Use a smaller PDF file or process specific pages")
        elif isinstance(e, UnsupportedFileError):
            return user_input_error(str(e), hint="Ensure the file is a valid PDF")
        else:
            return forbidden_error(str(e))
    except FileNotFoundError as e:
        await send_event({"type": "error", "message": str(e)})
        return not_found_error(str(e))
    except Exception as e:
        await send_event({"type": "error", "message": f"Processing failed: {str(e)}"})
        return internal_error("Failed to stream PDF extraction", detail=str(e))