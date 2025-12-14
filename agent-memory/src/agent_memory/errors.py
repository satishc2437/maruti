"""
Error taxonomy for Agent Memory MCP.
All errors are explicit and non-destructive.
"""

from typing import Any, Dict, Optional


def user_input_error(message: str, hint: Optional[str] = None) -> Dict[str, Any]:
    err: Dict[str, Any] = {"ok": False, "error": "UserInput", "message": message}
    if hint:
        err["hint"] = hint
    return err

def forbidden_error(message: str, hint: Optional[str] = None) -> Dict[str, Any]:
    err: Dict[str, Any] = {"ok": False, "error": "Forbidden", "message": message}
    if hint:
        err["hint"] = hint
    return err

def not_found_error(message: str, hint: Optional[str] = None) -> Dict[str, Any]:
    err: Dict[str, Any] = {"ok": False, "error": "NotFound", "message": message}
    if hint:
        err["hint"] = hint
    return err

def internal_error(message: str, detail: Optional[str] = None) -> Dict[str, Any]:
    err: Dict[str, Any] = {"ok": False, "error": "Internal", "message": message}
    if detail:
        err["detail"] = detail
    return err

def timeout_error(message: str) -> Dict[str, Any]:
    return {"ok": False, "error": "Timeout", "message": message}

def invalid_section_error(section: str) -> Dict[str, Any]:
    return {"ok": False, "error": "InvalidSection", "message": f"Section '{section}' is not defined in schema"}
