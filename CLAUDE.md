# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

Maruti is a monorepo of self-contained **Model Context Protocol (MCP) tools/servers**, plus a set of Copilot/agent definitions that consume them. It is a `uv` workspace: each tool under `mcp-tools/<name>/` is its own independently releasable Python project with its own `pyproject.toml`, `src/`, `tests/`, and `README.md`.

Python **3.14** is the repo standard (`requires-python = ">=3.14"` on every project).

## Workspace Layout (big-picture)

- `mcp-tools/<name>/` — one MCP server per folder. Current members: `agent-memory`, `pdf-reader`, `xlsx-reader`. Members are declared in the root `pyproject.toml` under `[tool.uv.workspace]`.
- `agents/<name>/` — project-owned Copilot/agent definitions (`*.agent.md` + an `<name>-internals/` directory with `rules.json` and supporting assets). Agents load their internals deterministically before any action (see any `*.agent.md`'s "Deterministic Rules" preamble).
- `.github/agents/` — Copilot chat-mode agents for use in **this** repo. Populated by symlinks into `agents/` (see `scripts/link_agents.py`).
- `.github/agent-memory/<agent>/` — runtime memory written by the `agent-memory` MCP server for agents running against this repo. Contents are data, not source.
- `docs/` — repo-level documentation: `Constitution.md` (binding principles, agent-readable MUST/SHOULD), `specs-template.md`, etc.
- `.devcontainer/` — the canonical development environment. `post-create.sh` and `add-mcp-server.sh` auto-discover any `mcp-tools/<tool>/pyproject.toml` that mentions "mcp" and install it editable.
- Per-tool `mcp-tools/<tool>/specs/` holds that tool's specs (see `docs/specs-template.md`).

## Core Architectural Rules

These are enforced by `docs/Constitution.md` and matter for every change:

1. **Tool isolation (MUST).** Code in one `mcp-tools/<a>/` MUST NOT import from another `mcp-tools/<b>/`. There is no shared internal library. If real sharing is needed, promote it to an external package — do not create a repo-internal shared module.
2. **Tool-local everything.** Each tool owns its own `pyproject.toml`, `src/<pkg>/`, `tests/`, and `README.md`. Keep PRs scoped to a single tool when possible.
3. **uv/uvx distribution contract.** Every tool must be runnable both as `uv run <tool>` locally and via `uvx --from "git+https://github.com/satishc2437/maruti.git@<ref>#subdirectory=mcp-tools/<tool>" python -m <module>`. Each tool's README must contain a working `uvx` snippet.
4. **MCP stdio servers.** Tools follow a `src/<pkg>/__main__.py` → `server.py` pattern that registers MCP tools/resources and speaks JSON-RPC over stdio. The `mcp` import is guarded so tests can import tool code without the MCP runtime.
5. **Devcontainer-first.** Everything (creation, install, run, lint, test) must work inside the dev container. No undocumented host-only steps.

## Commands

Run from the repo root unless noted. The repo is a `uv` workspace — `uv sync` at the root without `--all-packages` can remove per-tool deps; always use `--all-packages` when you need the full test env.

```bash
# Full workspace sync (use this for root-level testing)
uv sync --dev --all-packages

# Run a specific tool (console scripts declared per-tool)
uv run agent-memory
uv run pdf-reader
uv run xlsx-reader

# Tests — all workspace packages
uv run pytest

# Tests — single tool
uv run pytest mcp-tools/pdf-reader -v

# Tests — single test node
uv run pytest mcp-tools/pdf-reader/tests/test_foo.py::test_bar -v

# Per-tool work (faster iteration, uses tool's local dev deps)
cd mcp-tools/<tool> && uv sync --dev && uv run pytest
```

### Quality gates (all must pass — these are the CI-relevant checks)

```bash
# Docstring lint (Google convention, ruff pydocstyle D* rules)
# Scope is intentionally limited to mcp-tools/*/src — tests are excluded by config.
uv run ruff check --select D mcp-tools/*/src

# Pylint: MUST exit 0 (zero errors AND zero warnings).
# Uses root .pylintrc which disables C (convention) and R (refactor) — only E/W/F count.
uv run pylint mcp-tools/*/src

# Coverage gate: >95% per tool (enforced in each tool's pyproject via --cov-fail-under=95).
cd mcp-tools/<tool> && uv run pytest --cov --cov-fail-under=95
```

## Adding a New MCP Tool

1. Create `mcp-tools/<name>/` with its own `pyproject.toml` declaring `requires-python = ">=3.14"` and mentioning `mcp` (devcontainer auto-discovery keys on the literal string "mcp" in the project file).
2. Add the path to `[tool.uv.workspace].members` in the root `pyproject.toml`.
3. Layout: `src/<pkg>/{__init__.py, __main__.py, server.py}` plus `tests/`. Follow the `agent-memory` pattern — `__main__.py` dispatches to `server.run_server()` via `asyncio.run`.
4. Declare a `[project.scripts]` entry so `uv run <tool>` works.
5. Write a README with a copy/pasteable `uvx` snippet targeting `github.com/satishc2437/maruti`.
6. Rebuild the devcontainer (or run `.devcontainer/post-create.sh`) so auto-discovery installs it editable.

## Definition of Done (per tool)

- Runs in-container via `uv run <tool>` and via `uvx` from GitHub.
- `ruff check --select D` passes with zero docstring warnings.
- `pylint` passes with zero E/W/F messages.
- Coverage ≥ 95% on that tool.
- Public MCP surface (tool names, parameters, outputs) is documented and treated as a stable contract — prefer backward-compatible changes.

## Governance

`docs/Constitution.md` is the binding source of truth for principles and quality gates. When a constitution rule and this file disagree, the constitution wins — update this file to match.
