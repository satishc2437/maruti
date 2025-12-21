"""Error handling and taxonomy for Agent Memory MCP Server.

Implements consistent error classification and formatting for
all memory operations.
"""

import logging
import uuid
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def user_input_error(message: str, hint: Optional[str] = None, correlation_id: Optional[str] = None) -> Dict[str, Any]:
    """Return structured UserInput error."""
    error_id = correlation_id or uuid.uuid4().hex[:8]
    logger.info(f"UserInput error [{error_id}]: {message}")

    error = {
        "ok": False,
        "code": "UserInput",
        "message": message,
        "correlation_id": error_id
    }

    if hint:
        error["hint"] = hint

    return error


def forbidden_error(message: str, correlation_id: Optional[str] = None) -> Dict[str, Any]:
    """Return structured Forbidden error."""
    error_id = correlation_id or uuid.uuid4().hex[:8]
    logger.warning(f"Forbidden error [{error_id}]: {message}")

    return {
        "ok": False,
        "code": "Forbidden",
        "message": message,
        "correlation_id": error_id
    }


def not_found_error(message: str, correlation_id: Optional[str] = None) -> Dict[str, Any]:
    """Return structured NotFound error."""
    error_id = correlation_id or uuid.uuid4().hex[:8]
    logger.info(f"NotFound error [{error_id}]: {message}")

    return {
        "ok": False,
        "code": "NotFound",
        "message": message,
        "correlation_id": error_id
    }


def timeout_error(message: str, correlation_id: Optional[str] = None) -> Dict[str, Any]:
    """Return structured Timeout error."""
    error_id = correlation_id or uuid.uuid4().hex[:8]
    logger.warning(f"Timeout error [{error_id}]: {message}")

    return {
        "ok": False,
        "code": "Timeout",
        "message": message,
        "correlation_id": error_id
    }


def internal_error(message: str, detail: Optional[str] = None, correlation_id: Optional[str] = None) -> Dict[str, Any]:
    """Return structured Internal error."""
    error_id = correlation_id or uuid.uuid4().hex[:8]
    logger.error(f"Internal error [{error_id}]: {message} - {detail}")

    error = {
        "ok": False,
        "code": "Internal",
        "message": message,
        "correlation_id": error_id
    }

    if detail:
        # Truncate detail to avoid exposing too much information
        error["detail"] = detail[:200] if len(detail) > 200 else detail

    return error


def cancellation_error(message: str, correlation_id: Optional[str] = None) -> Dict[str, Any]:
    """Return structured Cancelled error."""
    error_id = correlation_id or uuid.uuid4().hex[:8]
    logger.info(f"Cancellation [{error_id}]: {message}")

    return {
        "ok": False,
        "code": "Cancelled",
        "message": message,
        "correlation_id": error_id
    }
