"""
Schema utilities for Agent Memory MCP.
- Provide default v1 schema text.
- Validate sections and schema presence.
- Generate session log headers deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

DEFAULT_SCHEMA_VERSION = "v1"

SCHEMA_V1_TEXT = """# Agent Memory Schema v1

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

ALLOWED_SECTIONS_V1: List[str] = [
    "Context",
    "Discussion Summary",
    "Decisions",
    "Open Questions",
    "Next Actions",
]

@dataclass(frozen=True)
class SessionHeader:
    agent_name: str
    date: str  # YYYY-MM-DD
    session_id: str

def ensure_schema_file(schema_path: Path) -> Tuple[str, bool]:
    """
    Ensure _schema.md exists with at least v1 text.
    Returns (version, created_flag).
    """
    created = False
    if not schema_path.exists():
        schema_path.write_text(SCHEMA_V1_TEXT, encoding="utf-8")
        created = True
    else:
        # If file exists but empty, initialize
        if schema_path.stat().st_size == 0:
            schema_path.write_text(SCHEMA_V1_TEXT, encoding="utf-8")
            created = True

    # Detect version by naive header parse (explicit declaration preferred)
    text = schema_path.read_text(encoding="utf-8")
    version = DEFAULT_SCHEMA_VERSION
    if "Schema v1" in text:
        version = "v1"
    # Future: parse explicit "Schema vX" lines
    return version, created

def validate_section(section: str, schema_version: str = DEFAULT_SCHEMA_VERSION) -> bool:
    """Return True if section is allowed by the schema version."""
    if schema_version == "v1":
        return section in ALLOWED_SECTIONS_V1
    # Unknown versions: conservative deny
    return False

def generate_session_header_md(header: SessionHeader) -> str:
    """Render deterministic Markdown header for a new session file."""
    return (
        f"# Session Log\n\n"
        f"**Agent Name:** {header.agent_name}\n"
        f"**Date:** {header.date}\n"
        f"**Session ID:** {header.session_id}\n\n"
        f"## Context\n\n"
        f"## Discussion Summary\n\n"
        f"## Decisions\n\n"
        f"## Open Questions\n\n"
        f"## Next Actions\n"
    )

def find_section_offsets(md_text: str) -> Dict[str, int]:
    """
    Return map of section heading -> start index in lines.
    Looks for H2 headings (## Section).
    """
    lines = md_text.splitlines()
    offsets: Dict[str, int] = {}
    for idx, line in enumerate(lines):
        if line.startswith("## "):
            name = line[3:].strip()
            offsets[name] = idx
    return offsets

def append_under_section(md_text: str, section: str, content: str) -> str:
    """
    Append content under a section heading while preserving existing text.
    Insert a bullet or paragraph, deterministic newline handling.
    """
    lines = md_text.splitlines()
    offsets = find_section_offsets(md_text)
    if section not in offsets:
        raise ValueError(f"Section '{section}' not found in document")

    # Find insertion point: after the heading line, before next heading or EOF.
    start = offsets[section] + 1
    end = len(lines)
    # Determine next heading boundary
    for idx in range(start, len(lines)):
        if lines[idx].startswith("## "):
            end = idx
            break

    # Ensure at least a blank line after heading
    if start < len(lines) and (lines[start].strip() != ""):
        lines.insert(start, "")

    insertion = content.strip()
    # Deterministic: prefix with "- " for list-like content if it is single-line without Markdown markers
    bullet = f"- {insertion}" if "\n" not in insertion and not insertion.startswith(("#", "-", "*")) else insertion
    # Insert at end boundary
    lines.insert(end, bullet)
    # Ensure trailing newline
    out = "\n".join(lines).rstrip() + "\n"
    return out
