# Implementation Plan: Repo-Wide Docstrings & Docstring-Lint Gate

**Branch**: `main` | **Date**: 2025-12-21 | **Spec**: `specs/main/spec.md`
**Input**: Feature specification from `/specs/main/spec.md`

## Summary

Add consistent docstrings across the Python codebase and enforce a docstring-specific lint gate with zero warnings.

## Technical Context

**Language/Version**: Python 3.14
**Primary Dependencies**: `uv`, `pytest`, `pytest-cov`
**Lint/Docstring Checks**: Adopt `ruff` with pydocstyle rules (`D*`) enabled, using the Google docstring convention.
**Project Type**: Tool monorepo (this repository)

## Constitution Check

Gates required for this repo/tool monorepo:

- linting passes with zero errors
- docstring checks pass with zero warnings
- tests are present and meaningful
- coverage requirements (>95% per tool)

## Scope Decisions

**Docstring-lint scope**: `main.py` + `mcp-tools/*/src/**`.

**Default exclusions**: `**/tests/**`, `.specify/**`, `**/__pycache__/**`.

**Canonical docstring check**: `uv run ruff check --select D <scope>`.

## Project Structure

This repository is a tool monorepo:

```text
mcp-tools/<tool-name>/
├── pyproject.toml
├── README.md
├── src/
│   └── <tool_package>/
└── tests/
```

**Structure Decision**: Keep the canonical ruff docstring configuration at the repo root (for `main.py` and as the source of truth). Tool-local `pyproject.toml` ruff config is only added if needed for running checks from within a tool directory, and MUST mirror the root settings to avoid drift.

## Implementation Strategy

1. Add `ruff` as a dev dependency where needed.
2. Configure ruff to enable docstring checks (pydocstyle `D` rules) and pick a convention.
3. Run docstring lint, then add/update docstrings to eliminate warnings.
4. Ensure docstrings cover public APIs (modules/classes/functions that are imported/used externally).
