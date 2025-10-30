"""
Error taxonomy and handling utilities for the Excel Reader MCP server.
Provides structured error responses with consistent classification.
"""

from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


def user_input_error(
    message: str, hint: Optional[str] = None, **kwargs
) -> Dict[str, Any]:
    """Return a structured UserInput error response."""
    error = {"ok": False, "code": "UserInput", "message": message}
    if hint:
        error["hint"] = hint
    if kwargs:
        error.update(kwargs)
    return error


def forbidden_error(message: str, **kwargs) -> Dict[str, Any]:
    """Return a structured Forbidden error response."""
    error = {"ok": False, "code": "Forbidden", "message": message}
    if kwargs:
        error.update(kwargs)
    return error


def not_found_error(message: str, **kwargs) -> Dict[str, Any]:
    """Return a structured NotFound error response."""
    error = {"ok": False, "code": "NotFound", "message": message}
    if kwargs:
        error.update(kwargs)
    return error


def timeout_error(message: str, **kwargs) -> Dict[str, Any]:
    """Return a structured Timeout error response."""
    error = {"ok": False, "code": "Timeout", "message": message}
    if kwargs:
        error.update(kwargs)
    return error


def internal_error(
    message: str, detail: Optional[str] = None, **kwargs
) -> Dict[str, Any]:
    """Return a structured Internal error response."""
    error = {"ok": False, "code": "Internal", "message": message}
    if detail:
        error["detail"] = detail[:160]  # Truncate long details
        logger.error(f"Internal error: {message} - {detail}")
    if kwargs:
        error.update(kwargs)
    return error


def cancellation_error(message: str, **kwargs) -> Dict[str, Any]:
    """Return a structured Cancelled error response."""
    error = {"ok": False, "code": "Cancelled", "message": message}
    if kwargs:
        error.update(kwargs)
    return error


def success_response(data: Any, **kwargs) -> Dict[str, Any]:
    """Return a structured success response."""
    response = {"ok": True, "data": data}
    if kwargs:
        response.update(kwargs)
    return response


class ExcelProcessingError(Exception):
    """Base exception for Excel processing errors."""

    pass


class FileAccessError(ExcelProcessingError):
    """Raised when file access is denied or fails."""

    pass


class ValidationError(ExcelProcessingError):
    """Raised when parameter validation fails."""

    pass


class WorkbookError(ExcelProcessingError):
    """Raised when workbook operations fail."""

    pass


class WorksheetError(ExcelProcessingError):
    """Raised when worksheet operations fail."""

    pass


class ChartError(ExcelProcessingError):
    """Raised when chart operations fail."""

    pass


class PivotTableError(ExcelProcessingError):
    """Raised when pivot table operations fail."""

    pass
