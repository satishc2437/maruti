# Root-Level Removal Candidates (Review Only)

This file lists items at the repository root that may be unnecessary after the
migration to the `mcp-tools/` structure.

**Important**: This is a review list only. Nothing has been deleted.

## Likely Keep

- `.devcontainer/` — required for devcontainer-first workflow
- `.github/` — repo automation, agent configs, prompts
- `.specify/` — spec-kit templates and constitution
- `mcp-tools/` — all MCP tools (monorepo content)
- `pyproject.toml`, `uv.lock` — uv workspace definition and lockfile
- `README.md` — repo entry documentation
- `LICENSE` — licensing
- `MCP_DEVELOPMENT_WORKFLOW.md` — contributor workflow documentation

## Review / Optional

- `.vscode/` — editor settings; keep if you rely on VS Code workspace settings
- `maruti.code-workspace` — optional VS Code workspace file; can be removed if unused
- `.roo/`, `.roomodes` — tool-specific artifacts; keep only if actively used
- `.venv/` — local environment cache; often should not be committed (confirm whether tracked)

## Likely Remove (Pending Your Confirmation)

- `main.py` — appears to be a leftover root script and not part of the `mcp-tools/` layout

## Notes

- If you confirm removals, I can:
  1) verify whether each candidate is tracked by Git and referenced anywhere,
  2) remove it safely,
  3) update docs if needed.
