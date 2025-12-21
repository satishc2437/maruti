# app Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-12-21

## Active Technologies

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

- 001-mcp-tools-restructure: Added Python 3.14 + uv/uvx (workspace + execution), `mcp` (per-tool), standard Python packaging via `pyproject.toml`

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
