"""
Filesystem safety guards for Agent Memory MCP.
- Confine all file operations to the provided repo_root.
- Prevent path traversal outside allowed root.
- Enforce file size and directory listing limits.
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

FILE_SIZE_MAX_BYTES = 1_048_576  # 1 MiB default
DIRECTORY_LISTING_LIMIT = 1000

def ensure_repo_root(repo_root: str) -> Path:
    """Resolve and validate repo_root as an existing directory."""
    root = Path(repo_root).resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError("Repository root must exist and be a directory")
    return root

def resolve_under_root(root: Path, relative: str | Path) -> Path:
    """
    Resolve a path under root safely.
    Accepts absolute or relative; absolute must be within root.
    """
    candidate = Path(relative)
    if candidate.is_absolute():
        # Ensure absolute path is inside root
        resolved = candidate.resolve()
        if not str(resolved).startswith(str(root)):
            raise ValueError("Path outside allowed repo_root")
        return resolved
    # Treat as relative to root
    resolved = (root / candidate).resolve()
    if not str(resolved).startswith(str(root)):
        raise ValueError("Path outside allowed repo_root")
    return resolved

def ensure_dir(path: Path) -> None:
    """Create directory if missing (non-destructive)."""
    path.mkdir(parents=True, exist_ok=True)

def check_file_size_bounds(content: str) -> None:
    """Raise if content exceeds max size."""
    if len(content.encode("utf-8")) > FILE_SIZE_MAX_BYTES:
        raise ValueError("Content exceeds file size limit")

def limit_listing(items: list[str]) -> list[str]:
    """Apply deterministic listing cap."""
    return items[:DIRECTORY_LISTING_LIMIT]

def ensure_agent_memory_layout(root: Path, agent_name: str) -> Tuple[Path, Path, Path]:
    """
    Ensure base layout:
      .github/agent-memory/<agent_name>/{logs,_summary.md,_schema.md}
    Returns tuple: (agent_dir, logs_dir, summary_file_path)
    """
    base = resolve_under_root(root, ".github/agent-memory")
    ensure_dir(base)
    agent_dir = base / agent_name
    ensure_dir(agent_dir)
    logs_dir = agent_dir / "logs"
    ensure_dir(logs_dir)
    summary = agent_dir / "_summary.md"
    schema = agent_dir / "_schema.md"
    # Create files if missing (empty templates handled by tools/schemas)
    summary.touch(exist_ok=True)
    schema.touch(exist_ok=True)
    return agent_dir, logs_dir, summary
