# app Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-12-21

## Active Technologies
- Python 3.14 + `mcp` (stdio MCP server), `httpx` (GitHub REST calls), `PyJWT` + `cryptography` (GitHub App JWT signing) (002-github-app-mcp)
- Local audit log sink (JSON lines to stderr and/or optional file); no database (002-github-app-mcp)
- Python 3.14 + `mcp`, `httpx`, `PyJWT`, `cryptography` (003-github-project-tasks)
- Optional JSONL audit file sink (host-provided absolute path); otherwise stderr/logging (003-github-project-tasks)

- Python 3.14 + uv/uvx (workspace + execution), `mcp` (per-tool), standard Python packaging via `pyproject.toml` (001-mcp-tools-restructure)

## Project Structure

```text
.
├── mcp-tools/
│   ├── agent-memory/
│   ├── onenote-reader/
│   ├── pdf-reader/
│   └── xlsx-reader/
├── specs/
└── pyproject.toml
```

## Commands

- `uv sync --dev`
- `uv run pytest`

## Code Style

Python 3.14: Follow standard conventions

## Recent Changes
- 003-github-project-tasks: Added Python 3.14 + `mcp`, `httpx`, `PyJWT`, `cryptography`
- 002-github-app-mcp: Added Python 3.14 + `mcp` (stdio MCP server), `httpx` (GitHub REST calls), `PyJWT` + `cryptography` (GitHub App JWT signing)

- 001-mcp-tools-restructure: Added Python 3.14 + uv/uvx (workspace + execution), `mcp` (per-tool), standard Python packaging via `pyproject.toml`

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
