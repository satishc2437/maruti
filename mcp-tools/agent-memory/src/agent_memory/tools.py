"""
Memory tools for Agent Memory MCP server.

Implements tool adapters that wrap memory operations with
validation, error handling, and MCP-compatible interfaces.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from .errors import (
    cancellation_error,
    forbidden_error,
    internal_error,
    not_found_error,
    timeout_error,
    user_input_error,
)
from .memory_ops import MemoryManager
from .safety import (
    InvalidRepositoryError,
    MemorySafetyError,
    PathTraversalError,
    SchemaValidationError,
)

logger = logging.getLogger(__name__)

# Tool metadata for MCP registration
TOOL_METADATA = {
    "start_session": {
        "description": "Creates or opens a session log for an agent on a given date",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": "Logical agent identifier (e.g. 'aristotle')"
                },
                "repo_root": {
                    "type": "string",
                    "description": "Absolute path to repository root"
                },
                "date": {
                    "type": "string",
                    "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    "description": "Date in YYYY-MM-DD format (defaults to current date)"
                }
            },
            "required": ["agent_name", "repo_root"]
        }
    },
    "append_entry": {
        "description": "Appends structured content to a specific section of the session log",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": "Logical agent identifier"
                },
                "repo_root": {
                    "type": "string",
                    "description": "Absolute path to repository root"
                },
                "date": {
                    "type": "string",
                    "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    "description": "Date in YYYY-MM-DD format (defaults to current date)"
                },
                "section": {
                    "type": "string",
                    "enum": ["Context", "Discussion Summary", "Decisions", "Open Questions", "Next Actions"],
                    "description": "Section name from schema"
                },
                "content": {
                    "type": "string",
                    "description": "Content to append to the section"
                }
            },
            "required": ["agent_name", "repo_root", "section", "content"]
        }
    },
    "read_summary": {
        "description": "Reads the canonical persistent summary for an agent",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": "Logical agent identifier"
                },
                "repo_root": {
                    "type": "string",
                    "description": "Absolute path to repository root"
                }
            },
            "required": ["agent_name", "repo_root"]
        }
    },
    "update_summary": {
        "description": "Updates a specific section of the agent summary",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": "Logical agent identifier"
                },
                "repo_root": {
                    "type": "string",
                    "description": "Absolute path to repository root"
                },
                "section": {
                    "type": "string",
                    "description": "Section name to update"
                },
                "content": {
                    "type": "string",
                    "description": "Content to add or replace"
                },
                "mode": {
                    "type": "string",
                    "enum": ["append", "replace"],
                    "description": "Whether to append to or replace section content"
                }
            },
            "required": ["agent_name", "repo_root", "section", "content", "mode"]
        }
    },
    "list_sessions": {
        "description": "Lists existing session logs for an agent",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": "Logical agent identifier"
                },
                "repo_root": {
                    "type": "string",
                    "description": "Absolute path to repository root"
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum number of sessions to return"
                }
            },
            "required": ["agent_name", "repo_root"]
        }
    }
}


def validate_start_session_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Validate parameters for start_session tool."""
    agent_name = params.get("agent_name")
    if not agent_name or not isinstance(agent_name, str):
        raise ValueError("Parameter 'agent_name' is required and must be a string")

    repo_root = params.get("repo_root")
    if not repo_root or not isinstance(repo_root, str):
        raise ValueError("Parameter 'repo_root' is required and must be a string")

    date = params.get("date")
    if date is not None and not isinstance(date, str):
        raise ValueError("Parameter 'date' must be a string in YYYY-MM-DD format")

    return {
        "agent_name": agent_name,
        "repo_root": repo_root,
        "date": date
    }


def validate_append_entry_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Validate parameters for append_entry tool."""
    agent_name = params.get("agent_name")
    if not agent_name or not isinstance(agent_name, str):
        raise ValueError("Parameter 'agent_name' is required and must be a string")

    repo_root = params.get("repo_root")
    if not repo_root or not isinstance(repo_root, str):
        raise ValueError("Parameter 'repo_root' is required and must be a string")

    section = params.get("section")
    if not section or not isinstance(section, str):
        raise ValueError("Parameter 'section' is required and must be a string")

    content = params.get("content")
    if not content or not isinstance(content, str):
        raise ValueError("Parameter 'content' is required and must be a string")

    date = params.get("date")
    if date is not None and not isinstance(date, str):
        raise ValueError("Parameter 'date' must be a string in YYYY-MM-DD format")

    return {
        "agent_name": agent_name,
        "repo_root": repo_root,
        "section": section,
        "content": content,
        "date": date
    }


def validate_basic_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Validate basic agent_name and repo_root parameters."""
    agent_name = params.get("agent_name")
    if not agent_name or not isinstance(agent_name, str):
        raise ValueError("Parameter 'agent_name' is required and must be a string")

    repo_root = params.get("repo_root")
    if not repo_root or not isinstance(repo_root, str):
        raise ValueError("Parameter 'repo_root' is required and must be a string")

    return {
        "agent_name": agent_name,
        "repo_root": repo_root
    }


def validate_update_summary_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Validate parameters for update_summary tool."""
    basic = validate_basic_params(params)

    section = params.get("section")
    if not section or not isinstance(section, str):
        raise ValueError("Parameter 'section' is required and must be a string")

    content = params.get("content")
    if not content or not isinstance(content, str):
        raise ValueError("Parameter 'content' is required and must be a string")

    mode = params.get("mode")
    if not mode or mode not in ["append", "replace"]:
        raise ValueError("Parameter 'mode' is required and must be 'append' or 'replace'")

    return {
        **basic,
        "section": section,
        "content": content,
        "mode": mode
    }


def validate_list_sessions_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Validate parameters for list_sessions tool."""
    basic = validate_basic_params(params)

    limit = params.get("limit")
    if limit is not None:
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            raise ValueError("Parameter 'limit' must be an integer between 1 and 100")

    return {
        **basic,
        "limit": limit
    }


async def run_with_timeout(coro, timeout_seconds: float = 10.0):
    """Run coroutine with timeout protection."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        return timeout_error(f"Operation exceeded {timeout_seconds:.1f}s limit")


async def tool_start_session(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool: Create or open session log for an agent on a given date.
    """
    try:
        validated = validate_start_session_params(params or {})
    except ValueError as e:
        return user_input_error(str(e), hint="Check parameter types and values")

    try:
        async def start_operation():
            manager = MemoryManager(validated["repo_root"], validated["agent_name"])
            return manager.start_session(validated["date"])

        result = await run_with_timeout(start_operation(), timeout_seconds=10.0)

        if isinstance(result, dict) and not result.get("ok", True):
            return result  # Already an error response

        return {"ok": True, "data": result}

    except MemorySafetyError as e:
        if isinstance(e, PathTraversalError):
            return forbidden_error(str(e))
        elif isinstance(e, InvalidRepositoryError):
            return user_input_error(str(e), hint="Ensure repo_root points to a valid repository directory")
        else:
            return forbidden_error(str(e))
    except FileNotFoundError as e:
        return not_found_error(str(e))
    except Exception as e:
        return internal_error("Failed to start session", detail=str(e))


async def tool_append_entry(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool: Append content to a specific section of the session log.
    """
    try:
        validated = validate_append_entry_params(params or {})
    except ValueError as e:
        return user_input_error(str(e), hint="Check parameter types and values")

    try:
        async def append_operation():
            manager = MemoryManager(validated["repo_root"], validated["agent_name"])
            return manager.append_entry(
                validated["section"],
                validated["content"],
                validated["date"]
            )

        result = await run_with_timeout(append_operation(), timeout_seconds=10.0)

        if isinstance(result, dict) and not result.get("ok", True):
            return result  # Already an error response

        return {"ok": True, "data": result}

    except MemorySafetyError as e:
        if isinstance(e, PathTraversalError):
            return forbidden_error(str(e))
        elif isinstance(e, InvalidRepositoryError):
            return user_input_error(str(e), hint="Ensure repo_root points to a valid repository directory")
        elif isinstance(e, SchemaValidationError):
            return user_input_error(str(e), hint="Check that section name matches schema")
        else:
            return forbidden_error(str(e))
    except ValueError as e:
        return user_input_error(str(e), hint="Check section name and date format")
    except FileNotFoundError as e:
        return not_found_error(str(e))
    except Exception as e:
        return internal_error("Failed to append entry", detail=str(e))


async def tool_read_summary(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool: Read the canonical persistent summary for an agent.
    """
    try:
        validated = validate_basic_params(params or {})
    except ValueError as e:
        return user_input_error(str(e), hint="Provide valid agent_name and repo_root")

    try:
        async def read_operation():
            manager = MemoryManager(validated["repo_root"], validated["agent_name"])
            return manager.read_summary()

        result = await run_with_timeout(read_operation(), timeout_seconds=10.0)

        if isinstance(result, dict) and not result.get("ok", True):
            return result  # Already an error response

        return {"ok": True, "data": result}

    except MemorySafetyError as e:
        if isinstance(e, PathTraversalError):
            return forbidden_error(str(e))
        elif isinstance(e, InvalidRepositoryError):
            return user_input_error(str(e), hint="Ensure repo_root points to a valid repository directory")
        else:
            return forbidden_error(str(e))
    except FileNotFoundError as e:
        return not_found_error(str(e))
    except Exception as e:
        return internal_error("Failed to read summary", detail=str(e))


async def tool_update_summary(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool: Update a specific section of the agent summary.
    """
    try:
        validated = validate_update_summary_params(params or {})
    except ValueError as e:
        return user_input_error(str(e), hint="Check parameter types and values")

    try:
        async def update_operation():
            manager = MemoryManager(validated["repo_root"], validated["agent_name"])
            return manager.update_summary(
                validated["section"],
                validated["content"],
                validated["mode"]
            )

        result = await run_with_timeout(update_operation(), timeout_seconds=10.0)

        if isinstance(result, dict) and not result.get("ok", True):
            return result  # Already an error response

        return {"ok": True, "data": result}

    except MemorySafetyError as e:
        if isinstance(e, PathTraversalError):
            return forbidden_error(str(e))
        elif isinstance(e, InvalidRepositoryError):
            return user_input_error(str(e), hint="Ensure repo_root points to a valid repository directory")
        else:
            return forbidden_error(str(e))
    except ValueError as e:
        return user_input_error(str(e), hint="Check section name and mode parameter")
    except FileNotFoundError as e:
        return not_found_error(str(e))
    except Exception as e:
        return internal_error("Failed to update summary", detail=str(e))


async def tool_list_sessions(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool: List existing session logs for an agent.
    """
    try:
        validated = validate_list_sessions_params(params or {})
    except ValueError as e:
        return user_input_error(str(e), hint="Check parameter types and ranges")

    try:
        async def list_operation():
            manager = MemoryManager(validated["repo_root"], validated["agent_name"])
            return manager.list_sessions(validated["limit"])

        result = await run_with_timeout(list_operation(), timeout_seconds=10.0)

        if isinstance(result, dict) and not result.get("ok", True):
            return result  # Already an error response

        return {"ok": True, "data": result}

    except MemorySafetyError as e:
        if isinstance(e, PathTraversalError):
            return forbidden_error(str(e))
        elif isinstance(e, InvalidRepositoryError):
            return user_input_error(str(e), hint="Ensure repo_root points to a valid repository directory")
        else:
            return forbidden_error(str(e))
    except FileNotFoundError as e:
        return not_found_error(str(e))
    except Exception as e:
        return internal_error("Failed to list sessions", detail=str(e))
