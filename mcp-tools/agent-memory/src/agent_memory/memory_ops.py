"""
Core memory operations for Agent Memory MCP Server.

Implements the business logic for reading, writing, and managing
agent memory files according to the schema specification.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .safety import (
    SchemaValidationError,
    ensure_memory_path,
    sanitize_content,
    validate_agent_name,
    validate_date_format,
    validate_repository_root,
    validate_section_name,
)

# Schema version and allowed sections
SCHEMA_VERSION = "v1"
DEFAULT_ALLOWED_SECTIONS = [
    "Context",
    "Discussion Summary",
    "Decisions",
    "Open Questions",
    "Next Actions"
]

# Default schema content
DEFAULT_SCHEMA_CONTENT = """# Agent Memory Schema v1

## Header
- Agent Name
- Date (YYYY-MM-DD)
- Session ID

## Context
- Project
- Focus Area
- Stage

## Discussion Summary
- Key topics discussed

## Decisions
- Explicit decisions made

## Open Questions
- Unresolved issues or risks

## Next Actions
- Follow-up actions
"""

# Default summary template
DEFAULT_SUMMARY_TEMPLATE = """# Agent Summary

## Overview
- Current focus and objectives
- Recent progress

## Key Knowledge
- Important facts and insights
- Recurring themes

## Active Decisions
- Current decision points
- Pending resolutions

## Important Patterns
- Observed patterns and learnings
- Best practices discovered
"""


class MemoryManager:
    """Manages agent memory operations with schema validation."""

    def __init__(self, repo_root: Union[str, Path], agent_name: str):
        """
        Initialize memory manager for a specific agent and repository.

        Args:
            repo_root: Repository root path
            agent_name: Agent identifier
        """
        self.repo_root = validate_repository_root(repo_root)
        self.agent_name = validate_agent_name(agent_name)
        self.memory_path = ensure_memory_path(self.repo_root, self.agent_name)
        self.logs_path = self.memory_path / "logs"
        self.schema_path = self.memory_path / "_schema.md"
        self.summary_path = self.memory_path / "_summary.md"

        # Initialize schema and summary if they don't exist
        self._ensure_schema_exists()
        self._ensure_summary_exists()

    def _ensure_schema_exists(self) -> None:
        """Ensure schema file exists with default content."""
        if not self.schema_path.exists():
            self.schema_path.write_text(DEFAULT_SCHEMA_CONTENT, encoding='utf-8')

    def _ensure_summary_exists(self) -> None:
        """Ensure summary file exists with default template."""
        if not self.summary_path.exists():
            self.summary_path.write_text(DEFAULT_SUMMARY_TEMPLATE, encoding='utf-8')

    def _get_allowed_sections(self) -> List[str]:
        """Parse schema file to get allowed sections."""
        try:
            schema_content = self.schema_path.read_text(encoding='utf-8')

            # Extract sections from schema (lines starting with ##)
            sections = []
            for line in schema_content.split('\n'):
                line = line.strip()
                if line.startswith('## ') and not line.startswith('## Header'):
                    section_name = line[3:].strip()
                    sections.append(section_name)

            # Fall back to defaults if no sections found
            return sections if sections else DEFAULT_ALLOWED_SECTIONS

        except (OSError, UnicodeError):
            return DEFAULT_ALLOWED_SECTIONS

    def _get_session_file_path(self, date: Optional[str] = None) -> Path:
        """Get path to session log file for given date."""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        else:
            date = validate_date_format(date)

        return self.logs_path / f"{date}.md"

    def _create_session_header(self, date: str) -> str:
        """Create session file header according to schema."""
        session_id = datetime.now().strftime('%H%M%S')
        return f"""# Agent Memory Session

**Agent Name:** {self.agent_name}
**Date:** {date}
**Session ID:** {session_id}

---

"""

    def _find_section_in_content(self, content: str, section: str) -> tuple[int, int]:
        """
        Find section start and end positions in content.

        Returns:
            Tuple of (start_pos, end_pos) or (-1, -1) if not found
        """
        lines = content.split('\n')
        start_idx = -1
        end_idx = len(lines)

        # Find section header
        section_pattern = f"## {re.escape(section)}"
        for i, line in enumerate(lines):
            if re.match(section_pattern, line.strip()):
                start_idx = i
                break

        if start_idx == -1:
            return (-1, -1)

        # Find next section or end of file
        for i in range(start_idx + 1, len(lines)):
            if lines[i].strip().startswith('## '):
                end_idx = i
                break

        return (start_idx, end_idx)

    def start_session(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Create or open session log for given date.

        Args:
            date: Date in YYYY-MM-DD format (defaults to today)

        Returns:
            Dictionary with session_file path and created flag
        """
        session_file = self._get_session_file_path(date)
        created = False

        if not session_file.exists():
            # Create new session file with header
            actual_date = date or datetime.now().strftime('%Y-%m-%d')
            header = self._create_session_header(actual_date)

            # Add section placeholders
            allowed_sections = self._get_allowed_sections()
            content = header
            for section in allowed_sections:
                content += f"## {section}\n\n"

            session_file.write_text(content, encoding='utf-8')
            created = True

        return {
            "session_file": str(session_file.relative_to(self.repo_root)),
            "created": created
        }

    def append_entry(self, section: str, content: str, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Append content to a specific section of the session log.

        Args:
            section: Section name (must be in schema)
            content: Content to append
            date: Date in YYYY-MM-DD format (defaults to today)

        Returns:
            Success result with details
        """
        allowed_sections = self._get_allowed_sections()
        validate_section_name(section, allowed_sections)

        sanitized_content = sanitize_content(content)
        session_file = self._get_session_file_path(date)

        # Ensure session exists
        if not session_file.exists():
            self.start_session(date)

        # Read current content
        current_content = session_file.read_text(encoding='utf-8')

        # Find section
        start_idx, end_idx = self._find_section_in_content(current_content, section)

        if start_idx == -1:
            raise SchemaValidationError(f"Section '{section}' not found in session file")

        # Split content into lines
        lines = current_content.split('\n')

        # Find insertion point (after section header, before next section or end)
        insert_idx = start_idx + 1
        while insert_idx < end_idx and lines[insert_idx].strip() == '':
            insert_idx += 1

        # Format new entry with timestamp
        timestamp = datetime.now().strftime('%H:%M:%S')
        new_entry = f"- [{timestamp}] {sanitized_content}"

        # Insert the new entry
        lines.insert(insert_idx, new_entry)

        # Write back to file
        updated_content = '\n'.join(lines)
        session_file.write_text(updated_content, encoding='utf-8')

        return {
            "ok": True,
            "session_file": str(session_file.relative_to(self.repo_root)),
            "section": section,
            "entry_added": True
        }

    def read_summary(self) -> Dict[str, Any]:
        """
        Read the agent's persistent summary.

        Returns:
            Dictionary with summary content
        """
        try:
            summary_content = self.summary_path.read_text(encoding='utf-8')
            return {
                "summary": summary_content,
                "file_path": str(self.summary_path.relative_to(self.repo_root))
            }
        except FileNotFoundError:
            self._ensure_summary_exists()
            summary_content = self.summary_path.read_text(encoding='utf-8')
            return {
                "summary": summary_content,
                "file_path": str(self.summary_path.relative_to(self.repo_root))
            }

    def update_summary(self, section: str, content: str, mode: str = "append") -> Dict[str, Any]:
        """
        Update a specific section of the agent summary.

        Args:
            section: Section name
            content: Content to add/replace
            mode: "append" or "replace"

        Returns:
            Success result with details
        """
        if mode not in ["append", "replace"]:
            raise ValueError(f"Invalid mode '{mode}'. Must be 'append' or 'replace'")

        sanitized_content = sanitize_content(content)

        # Read current summary
        current_content = self.summary_path.read_text(encoding='utf-8')

        # Find section
        start_idx, end_idx = self._find_section_in_content(current_content, section)

        lines = current_content.split('\n')

        if start_idx == -1:
            # Section doesn't exist, add it at the end
            lines.append(f"## {section}")
            lines.append("")
            lines.append(sanitized_content)
        else:
            # Section exists
            if mode == "replace":
                # Replace content between section header and next section
                lines = lines[:start_idx+1] + ["", sanitized_content, ""] + lines[end_idx:]
            else:  # append
                # Insert before next section
                insert_idx = end_idx
                while insert_idx > start_idx and lines[insert_idx-1].strip() == '':
                    insert_idx -= 1
                lines.insert(insert_idx, sanitized_content)

        # Write back to file
        updated_content = '\n'.join(lines)
        self.summary_path.write_text(updated_content, encoding='utf-8')

        return {
            "ok": True,
            "summary_file": str(self.summary_path.relative_to(self.repo_root)),
            "section": section,
            "mode": mode,
            "updated": True
        }

    def list_sessions(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        List existing session logs for the agent.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            Dictionary with list of session files
        """
        if not self.logs_path.exists():
            return {"sessions": []}

        # Get all .md files in logs directory
        session_files = []
        for file in self.logs_path.glob("*.md"):
            if re.match(r'^\d{4}-\d{2}-\d{2}\.md$', file.name):
                session_files.append(file.name)

        # Sort by date (newest first)
        session_files.sort(reverse=True)

        # Apply limit if specified
        if limit and limit > 0:
            session_files = session_files[:limit]

        return {"sessions": session_files}

    def get_schema_info(self) -> Dict[str, Any]:
        """Get schema information and allowed sections."""
        allowed_sections = self._get_allowed_sections()
        schema_content = self.schema_path.read_text(encoding='utf-8')

        return {
            "schema_version": SCHEMA_VERSION,
            "allowed_sections": allowed_sections,
            "schema_file": str(self.schema_path.relative_to(self.repo_root)),
            "schema_content": schema_content
        }
