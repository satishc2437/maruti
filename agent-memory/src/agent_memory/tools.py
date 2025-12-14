"""
Agent Memory MCP Tools:
- start_session
- append_entry
- read_summary
- update_summary
- list_sessions
"""

from __future__ import annotations

import datetime as dt
import uuid
from pathlib import Path
from typing import Any, Dict, Tuple

from .errors import (internal_error, invalid_section_error, not_found_error,
                     user_input_error)
from .safety import (check_file_size_bounds, ensure_agent_memory_layout,
                     ensure_repo_root, limit_listing)
from .schemas import (SessionHeader, append_under_section, ensure_schema_file,
                      generate_session_header_md, validate_section)

TOOL_VERSION = "1.0.0"

def _validate_agent_and_root(params: Dict[str, Any]) -> Tuple[str, Path]:
    agent_name = params.get("agent_name")
    repo_root = params.get("repo_root")
    if not isinstance(agent_name, str) or not agent_name.strip():
        raise ValueError("Parameter 'agent_name' must be a non-empty string")
    if not isinstance(repo_root, str) or not repo_root.strip():
        raise ValueError("Parameter 'repo_root' must be a non-empty string")
    root = ensure_repo_root(repo_root)
    return agent_name.strip(), root

def _date_from_params(params: Dict[str, Any]) -> str:
    raw = params.get("date")
    if raw is None:
        return dt.date.today().isoformat()
    if not isinstance(raw, str):
        raise ValueError("Parameter 'date' must be string YYYY-MM-DD")
    # Minimal validation
    try:
        dt.date.fromisoformat(raw)
    except Exception:
        raise ValueError("Parameter 'date' must be YYYY-MM-DD")
    return raw

async def start_session(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create or open a session log file for agent_name on date.
    Returns: {"ok": true, "session_file": "...", "created": true|false, "version": TOOL_VERSION}
    """
    try:
        agent_name, root = _validate_agent_and_root(params)
        date = _date_from_params(params)

        agent_dir, logs_dir, summary = ensure_agent_memory_layout(root, agent_name)
        schema_path = agent_dir / "_schema.md"
        version, schema_created = ensure_schema_file(schema_path)

        session_md = logs_dir / f"{date}.md"
        created = False
        if not session_md.exists():
            # Create with deterministic header
            header = SessionHeader(agent_name=agent_name, date=date, session_id=uuid.uuid4().hex[:8])
            content = generate_session_header_md(header)
            check_file_size_bounds(content)
            session_md.write_text(content, encoding="utf-8")
            created = True

        return {"ok": True, "session_file": str(session_md), "created": created, "schema_version": version, "version": TOOL_VERSION}
    except ValueError as ve:
        return user_input_error(str(ve), hint="Check required params and formats")
    except Exception as exc:
        return internal_error("Failed to start session", detail=str(exc))

async def append_entry(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Append structured content to a specific section in the session log.
    Inputs: agent_name, repo_root, date?, section, content
    """
    try:
        agent_name, root = _validate_agent_and_root(params)
        date = _date_from_params(params)
        section = params.get("section")
        content = params.get("content")
        if not isinstance(section, str) or not section.strip():
            return user_input_error("Parameter 'section' must be a non-empty string")
        if not isinstance(content, str) or not content.strip():
            return user_input_error("Parameter 'content' must be a non-empty string")

        agent_dir, logs_dir, _summary = ensure_agent_memory_layout(root, agent_name)
        schema_path = agent_dir / "_schema.md"
        schema_version, _ = ensure_schema_file(schema_path)

        if not validate_section(section, schema_version):
            return invalid_section_error(section)

        session_md = logs_dir / f"{date}.md"
        if not session_md.exists():
            return not_found_error(f"Session file not found for date {date}", hint="Call start_session first")

        # Read, update deterministically, write back
        text = session_md.read_text(encoding="utf-8")
        updated = append_under_section(text, section, content)
        check_file_size_bounds(updated)
        session_md.write_text(updated, encoding="utf-8")
        return {"ok": True, "session_file": str(session_md), "section": section, "appended": True, "version": TOOL_VERSION}
    except ValueError as ve:
        return user_input_error(str(ve))
    except FileNotFoundError:
        return not_found_error("Session file missing unexpectedly")
    except Exception as exc:
        return internal_error("Failed to append entry", detail=str(exc))

async def read_summary(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Read _summary.md for the agent, creating a template if missing/empty.
    """
    try:
        agent_name, root = _validate_agent_and_root(params)
        agent_dir, _logs_dir, summary = ensure_agent_memory_layout(root, agent_name)
        schema_path = agent_dir / "_schema.md"
        version, _ = ensure_schema_file(schema_path)

        if summary.stat().st_size == 0:
            # Initialize minimal template
            tmpl = (
                f"# Agent Summary ({agent_name})\n\n"
                f"## Context\n\n"
                f"## Discussion Summary\n\n"
                f"## Decisions\n\n"
                f"## Open Questions\n\n"
                f"## Next Actions\n"
            )
            summary.write_text(tmpl, encoding="utf-8")

        return {"ok": True, "summary": summary.read_text(encoding="utf-8"), "schema_version": version, "version": TOOL_VERSION}
    except ValueError as ve:
        return user_input_error(str(ve))
    except Exception as exc:
        return internal_error("Failed to read summary", detail=str(exc))

async def update_summary(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a specific section of _summary.md.
    Inputs: agent_name, repo_root, section, content, mode in {'append','replace'}
    """
    try:
        agent_name, root = _validate_agent_and_root(params)
        section = params.get("section")
        content = params.get("content")
        mode = params.get("mode")
        if not isinstance(section, str) or not section.strip():
            return user_input_error("Parameter 'section' must be a non-empty string")
        if not isinstance(content, str):
            return user_input_error("Parameter 'content' must be a string")
        if mode not in ("append", "replace"):
            return user_input_error("Parameter 'mode' must be one of: append, replace")

        agent_dir, _logs_dir, summary = ensure_agent_memory_layout(root, agent_name)
        schema_path = agent_dir / "_schema.md"
        schema_version, _ = ensure_schema_file(schema_path)
        if not validate_section(section, schema_version):
            return invalid_section_error(section)

        text = summary.read_text(encoding="utf-8")
        if mode == "append":
            updated = append_under_section(text, section, content)
        else:
            # Replace contents under the section heading
            lines = text.splitlines()
            # locate section offsets
            from .schemas import find_section_offsets
            offsets = find_section_offsets(text)
            if section not in offsets:
                return invalid_section_error(section)
            start = offsets[section] + 1
            end = len(lines)
            for idx in range(start, len(lines)):
                if lines[idx].startswith("## "):
                    end = idx
                    break
            # ensure a blank line just after heading
            if start < len(lines) and lines[start].strip() != "":
                lines.insert(start, "")
                end += 1
            # splice replacement
            insertion = content.strip()
            block = insertion if insertion else ""
            new_lines = lines[:start] + ([block] if block else []) + lines[end:]
            updated = "\n".join(new_lines).rstrip() + "\n"

        check_file_size_bounds(updated)
        summary.write_text(updated, encoding="utf-8")
        return {"ok": True, "updated": True, "section": section, "mode": mode, "version": TOOL_VERSION}
    except ValueError as ve:
        return user_input_error(str(ve))
    except Exception as exc:
        return internal_error("Failed to update summary", detail=str(exc))

async def list_sessions(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    List existing session logs (YYYY-MM-DD.md) newest -> oldest.
    Optional: limit.
    """
    try:
        agent_name, root = _validate_agent_and_root(params)
        _agent_dir, logs_dir, _summary = ensure_agent_memory_layout(root, agent_name)
        if not logs_dir.exists():
            return {"ok": True, "sessions": []}
        entries = [p.name for p in logs_dir.iterdir() if p.is_file() and p.name.endswith(".md")]
        # Sort by date descending using filename
        def parse_date(name: str) -> str:
            # keep lexicographic sort (YYYY-MM-DD.md)
            return name
        sessions_sorted = sorted(entries, key=parse_date, reverse=True)
        limit = params.get("limit")
        if isinstance(limit, int) and limit > 0:
            sessions_sorted = sessions_sorted[:limit]
        sessions_sorted = limit_listing(sessions_sorted)
        return {"ok": True, "sessions": sessions_sorted}
    except ValueError as ve:
        return user_input_error(str(ve))
    except Exception as exc:
        return internal_error("Failed to list sessions", detail=str(exc))
