"""
Error taxonomy helpers for OneNote MCP server.

Provides consistent structured error objects:
  codes: UserInput | Forbidden | NotFound | Timeout | Internal
All error dicts share keys: ok(False), code, message, (optional) hint, detail, correlation_id.

Internal detail is truncated to avoid leaking sensitive data.
"""

from __future__ import annotations

import uuid
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def _new_id() -> str:
    return uuid.uuid4().hex[:10]


def _base(code: str, message: str, *, hint: Optional[str] = None,
          detail: Optional[str] = None, correlation_id: Optional[str] = None) -> Dict[str, Any]:
    cid = correlation_id or _new_id()
    err: Dict[str, Any] = {
        "ok": False,
        "code": code,
        "message": message,
        "correlation_id": cid
    }
    if hint:
        err["hint"] = hint
    if detail:
        err["detail"] = (detail[:400] + "...") if len(detail) > 400 else detail
    return err


def user_input_error(message: str, *, hint: Optional[str] = None,
                     correlation_id: Optional[str] = None) -> Dict[str, Any]:
    logger.info(f"UserInput[{correlation_id or 'new'}]: {message}")
    return _base("UserInput", message, hint=hint, correlation_id=correlation_id)


def forbidden_error(message: str, *, correlation_id: Optional[str] = None) -> Dict[str, Any]:
    logger.warning(f"Forbidden[{correlation_id or 'new'}]: {message}")
    return _base("Forbidden", message, correlation_id=correlation_id)


def not_found_error(message: str, *, correlation_id: Optional[str] = None) -> Dict[str, Any]:
    logger.info(f"NotFound[{correlation_id or 'new'}]: {message}")
    return _base("NotFound", message, correlation_id=correlation_id)


def timeout_error(message: str, *, correlation_id: Optional[str] = None) -> Dict[str, Any]:
    logger.warning(f"Timeout[{correlation_id or 'new'}]: {message}")
    return _base("Timeout", message, correlation_id=correlation_id)


def internal_error(message: str, *, detail: Optional[str] = None,
                   correlation_id: Optional[str] = None) -> Dict[str, Any]:
    logger.error(f"Internal[{correlation_id or 'new'}]: {message} detail={detail}")
    return _base("Internal", message, detail=detail, correlation_id=correlation_id)


def ensure_error(obj: Any) -> Dict[str, Any]:
    """
    Pass through already-structured error or wrap arbitrary object / string.
    """
    if isinstance(obj, dict) and obj.get("ok") is False and "code" in obj:
        return obj
    return internal_error("Unexpected error object", detail=str(obj))