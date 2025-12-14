"""
Safety validation and file guards for Agent Memory MCP Server.

Implements path validation and security constraints to ensure safe
memory operations within repository boundaries.
"""

import os
from pathlib import Path
from typing import Union


class MemorySafetyError(Exception):
    """Base exception for memory safety violations."""
    pass


class PathTraversalError(MemorySafetyError):
    """Raised when path attempts to escape repository root."""
    pass


class InvalidRepositoryError(MemorySafetyError):
    """Raised when repository root is invalid or inaccessible."""
    pass


class SchemaValidationError(MemorySafetyError):
    """Raised when memory entry doesn't conform to schema."""
    pass


def validate_repository_root(repo_root: Union[str, Path]) -> Path:
    """
    Validate and normalize repository root path.

    Args:
        repo_root: Repository root path (string or Path object)

    Returns:
        Resolved Path object if valid

    Raises:
        InvalidRepositoryError: If path is invalid or inaccessible
        PathTraversalError: If path contains dangerous patterns
    """
    # Convert to Path and resolve
    path = Path(os.path.expandvars(os.path.expanduser(str(repo_root)))).resolve()

    # Check for dangerous patterns
    path_str = str(path)
    if '..' in path_str or '~' in path_str:
        raise PathTraversalError(f"Repository path contains unsafe patterns: {repo_root}")

    # Check if directory exists
    if not path.exists():
        raise InvalidRepositoryError(f"Repository root does not exist: {repo_root}")

    # Check if it's actually a directory
    if not path.is_dir():
        raise InvalidRepositoryError(f"Repository root is not a directory: {repo_root}")

    # Check read/write access
    if not os.access(path, os.R_OK | os.W_OK):
        raise InvalidRepositoryError(f"Insufficient permissions for repository: {repo_root}")

    return path


def validate_agent_name(agent_name: str) -> str:
    """
    Validate agent name for filesystem safety.

    Args:
        agent_name: Agent identifier

    Returns:
        Sanitized agent name

    Raises:
        ValueError: If agent name is invalid
    """
    if not agent_name or not isinstance(agent_name, str):
        raise ValueError("Agent name must be a non-empty string")

    # Remove dangerous characters
    dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*', ' ']
    sanitized = agent_name.lower().strip()

    for char in dangerous_chars:
        if char in sanitized:
            raise ValueError(f"Agent name contains invalid character '{char}': {agent_name}")

    # Check length
    if len(sanitized) > 50:
        raise ValueError(f"Agent name too long (max 50 chars): {agent_name}")

    # Must start with letter or number
    if not sanitized[0].isalnum():
        raise ValueError(f"Agent name must start with letter or number: {agent_name}")

    return sanitized


def validate_date_format(date_str: str) -> str:
    """
    Validate date string format (YYYY-MM-DD).

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        Validated date string

    Raises:
        ValueError: If date format is invalid
    """
    import re
    from datetime import datetime

    if not date_str or not isinstance(date_str, str):
        raise ValueError("Date must be a non-empty string")

    # Check format with regex
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        raise ValueError(f"Date must be in YYYY-MM-DD format: {date_str}")

    # Validate actual date
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        raise ValueError(f"Invalid date: {date_str}")

    return date_str


def validate_section_name(section: str, allowed_sections: list) -> str:
    """
    Validate section name against schema.

    Args:
        section: Section name to validate
        allowed_sections: List of allowed section names

    Returns:
        Validated section name

    Raises:
        ValueError: If section is not allowed
    """
    if not section or not isinstance(section, str):
        raise ValueError("Section must be a non-empty string")

    if section not in allowed_sections:
        raise ValueError(f"Invalid section '{section}'. Allowed: {', '.join(allowed_sections)}")

    return section


def ensure_memory_path(repo_root: Path, agent_name: str) -> Path:
    """
    Ensure agent memory directory exists and return path.

    Args:
        repo_root: Validated repository root
        agent_name: Validated agent name

    Returns:
        Path to agent memory directory

    Raises:
        MemorySafetyError: If directory cannot be created
    """
    memory_path = repo_root / ".github" / "agent-memory" / agent_name

    try:
        memory_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (memory_path / "logs").mkdir(exist_ok=True)

        return memory_path
    except (OSError, PermissionError) as e:
        raise MemorySafetyError(f"Cannot create memory directory: {e}")


def get_safe_file_info(file_path: Path) -> dict:
    """
    Get safe file information without exposing sensitive paths.

    Args:
        file_path: Validated Path object

    Returns:
        Dictionary with safe file information
    """
    try:
        stat = file_path.stat()
        return {
            "filename": file_path.name,
            "size_bytes": stat.st_size,
            "modified_time": stat.st_mtime,
            "exists": True
        }
    except (OSError, FileNotFoundError):
        return {
            "filename": file_path.name,
            "exists": False
        }


def sanitize_content(content: str) -> str:
    """
    Sanitize content for safe storage.

    Args:
        content: Raw content string

    Returns:
        Sanitized content
    """
    if not isinstance(content, str):
        content = str(content)

    # Remove potentially dangerous content
    # (This is basic sanitization - extend as needed)
    sanitized = content.strip()

    # Limit content length
    max_length = 10000  # 10KB per entry
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "... [truncated]"

    return sanitized
