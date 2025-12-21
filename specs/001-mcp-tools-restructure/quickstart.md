# Quickstart: Validate the MCP Tools Restructure

**Feature**: `001-mcp-tools-restructure`
**Date**: 2025-12-21

## Prerequisites

- Use the repo devcontainer, or a local environment capable of running `uv`.

## Verify layout

- Confirm `mcp-tools/` exists and contains:
  - `mcp-tools/agent-memory/`
  - `mcp-tools/onenote-reader/`
  - `mcp-tools/pdf-reader/`
  - `mcp-tools/xlsx-reader/`

## Verify workspace dependencies

- From repo root:
  - `uv sync --dev --all-packages`

## Run tests

- From repo root:
  - `uv run pytest -q`

## Run per-tool coverage gates

- From repo root (run each tool independently):
  - `cd mcp-tools/agent-memory && uv run pytest --cov=agent_memory --cov-fail-under=95`
  - `cd mcp-tools/onenote-reader && uv run pytest --cov=onenote_reader --cov-fail-under=95`
  - `cd mcp-tools/pdf-reader && uv run pytest --cov=pdf_reader --cov-fail-under=95`
  - `cd mcp-tools/xlsx-reader && uv run pytest --cov=xlsx_reader --cov-fail-under=95`

## Spot-check tool docs

For each tool README under `mcp-tools/<tool>/README.md`:

- Local run instructions reference `mcp-tools/<tool>/` paths.
- A “no checkout” example exists using `uvx --from "git+https://github.com/<owner>/<repo>.git@<ref>#subdirectory=mcp-tools/<tool>" ...`.

## Confirm “no deletion without confirmation”

- Verify a repo-root removal-candidates report exists.
- Verify no repo-root files were deleted solely as part of cleanup.
