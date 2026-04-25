#!/usr/bin/env python3
"""Instantiate the MCP tool skeleton at templates/mcp-tool/ into mcp-tools/<name>/.

Usage:
    python scripts/new_mcp_tool.py <name> [--description "<one line>"]

Example:
    python scripts/new_mcp_tool.py image-processor \\
        --description "Extracts metadata and thumbnails from images."

What it does:
    1. Validates that <name> matches the lowercase-hyphen convention.
    2. Copies templates/mcp-tool/ to mcp-tools/<name>/, substituting four
       placeholders ({{TOOL_HYPHEN}}, {{TOOL_MODULE}}, {{TOOL_TITLE}},
       {{TOOL_DESCRIPTION}}) and renaming the src/__module__/ directory.
    3. Adds the new tool to [tool.uv.workspace].members in the root
       pyproject.toml.
    4. Prints a short list of follow-up commands.

This script is intentionally simple — no jinja2, no third-party deps. It
treats files as text, runs str.replace four times, and writes them back.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = REPO_ROOT / "templates" / "mcp-tool"
TOOLS_DIR = REPO_ROOT / "mcp-tools"
ROOT_PYPROJECT = REPO_ROOT / "pyproject.toml"

NAME_PATTERN = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")

# Files that are template-internal and should NOT be copied into the
# instantiated tool.
TEMPLATE_INTERNAL_FILES = {"README-TEMPLATE.md"}


def validate_name(name: str) -> None:
    """Raise SystemExit if name is not a valid lowercase-hyphen tool name."""
    if not NAME_PATTERN.match(name):
        sys.exit(
            f"Tool name {name!r} must be lowercase-hyphen, e.g. 'image-processor'. "
            "Use only [a-z0-9-], start with a letter, and don't use leading or "
            "doubled hyphens."
        )


def derive_substitutions(name: str, description: str) -> dict[str, str]:
    """Compute the four template placeholder values from the tool name."""
    tool_module = name.replace("-", "_")
    tool_title = " ".join(part.capitalize() for part in name.split("-"))
    return {
        "{{TOOL_HYPHEN}}": name,
        "{{TOOL_MODULE}}": tool_module,
        "{{TOOL_TITLE}}": tool_title,
        "{{TOOL_DESCRIPTION}}": description,
    }


def render_text(content: str, subs: dict[str, str]) -> str:
    """Apply every placeholder substitution to a string."""
    for placeholder, value in subs.items():
        content = content.replace(placeholder, value)
    return content


def copy_template(target: Path, subs: dict[str, str]) -> None:
    """Copy templates/mcp-tool/ to target with placeholder substitution.

    The src/__module__/ directory is renamed to src/<TOOL_MODULE>/ at
    copy time. Files listed in TEMPLATE_INTERNAL_FILES are skipped.
    """
    tool_module = subs["{{TOOL_MODULE}}"]
    for src_file in TEMPLATE_DIR.rglob("*"):
        if src_file.is_dir():
            continue
        rel = src_file.relative_to(TEMPLATE_DIR)
        if rel.name in TEMPLATE_INTERNAL_FILES:
            continue
        # Rename src/__module__/ to src/<tool_module>/ in the destination path.
        rel_parts = list(rel.parts)
        rel_parts = [tool_module if p == "__module__" else p for p in rel_parts]
        dest = target.joinpath(*rel_parts)
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            text = src_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            shutil.copyfile(src_file, dest)
            continue
        dest.write_text(render_text(text, subs), encoding="utf-8")


def add_to_workspace(name: str) -> None:
    """Insert mcp-tools/<name> into the root pyproject's workspace.members.

    Uses targeted string editing rather than a full TOML rewrite so the
    file's existing comments and formatting survive.
    """
    text = ROOT_PYPROJECT.read_text(encoding="utf-8")
    marker = "[tool.uv.workspace]"
    if marker not in text:
        sys.exit(f"Could not find {marker} block in {ROOT_PYPROJECT}.")

    new_member = f'    "mcp-tools/{name}",'
    if new_member in text:
        return  # already a member

    # Find the "members = [" opening, then the matching closing "]" line.
    members_pat = re.compile(r"members\s*=\s*\[\s*\n(.*?)^]", re.DOTALL | re.MULTILINE)
    match = members_pat.search(text)
    if not match:
        sys.exit("Could not parse [tool.uv.workspace].members in root pyproject.toml.")

    members_body = match.group(1)
    # Insert the new entry just before the closing bracket, in sorted order.
    existing = [
        line for line in members_body.splitlines() if line.strip().startswith('"mcp-tools/')
    ]
    existing.append(new_member)
    sorted_members = "\n".join(sorted(existing)) + "\n"
    new_text = text[: match.start(1)] + sorted_members + text[match.end(1) :]
    ROOT_PYPROJECT.write_text(new_text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Parse args, instantiate the template, register with the workspace."""
    parser = argparse.ArgumentParser(
        prog="new_mcp_tool",
        description="Instantiate templates/mcp-tool/ as a new MCP tool.",
    )
    parser.add_argument("name", help="lowercase-hyphen tool name (e.g. image-processor)")
    parser.add_argument(
        "--description",
        default="",
        help="One-line tool description; left blank if omitted.",
    )
    args = parser.parse_args(argv)

    validate_name(args.name)
    target = TOOLS_DIR / args.name
    if target.exists():
        sys.exit(f"Refusing to overwrite existing directory: {target.relative_to(REPO_ROOT)}")
    if not TEMPLATE_DIR.is_dir():
        sys.exit(f"Template not found at {TEMPLATE_DIR.relative_to(REPO_ROOT)}.")

    description = args.description or f"MCP server for {args.name}."
    subs = derive_substitutions(args.name, description)
    copy_template(target, subs)
    add_to_workspace(args.name)

    print(f"Created {target.relative_to(REPO_ROOT)} from templates/mcp-tool/.")
    print(f"Registered mcp-tools/{args.name} in workspace members.")
    print()
    print("Next steps:")
    print("  1. uv sync --dev --all-packages")
    print(f"  2. cd mcp-tools/{args.name} && uv run pytest")
    print(f"  3. Edit src/{subs['{{TOOL_MODULE}}']}/tools.py and server.py to define your real tools.")
    print("  4. Add a first spec under specs/001-<short-title>.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
