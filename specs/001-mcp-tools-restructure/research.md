# Research: MCP Tools Restructure

**Feature**: `001-mcp-tools-restructure`
**Date**: 2025-12-21

This feature is primarily a repository restructure and documentation/config alignment effort. The “research” here resolves small uncertainties around packaging/execution conventions and defines decision points.

## Decisions

### Decision: Standard stack for this repo
- **Decision**: Standardize on Python 3.14 with uv/uvx and a devcontainer-first workflow.
- **Rationale**: Matches the repo Constitution (Python 3.14, uv/uvx, devcontainer-first) and the current root `pyproject.toml`.
- **Alternatives considered**:
  - Mixed Python versions per tool → rejected due to drift and higher maintenance.
  - Poetry/pipenv → rejected because the repo already uses uv and Constitution mandates uv/uvx.

### Decision: Tool layout
- **Decision**: Keep a single repo-level `mcp-tools/` directory containing each tool as an independently packaged Python project.
- **Rationale**: Improves discoverability while preserving tool isolation and independent packaging.
- **Alternatives considered**:
  - Keep tools at repo root → rejected because it’s harder to distinguish tools from repo-level config.

### Decision: `uvx` GitHub invocation pattern
- **Decision**: Document a copy/paste pattern using `uvx --from "git+https://github.com/<owner>/<repo>.git@<ref>#subdirectory=mcp-tools/<tool>" python -m <package>`.
- **Rationale**: Supports “no checkout” usage and aligns with the Constitution’s distribution contract.
- **Alternatives considered**:
  - Requiring local checkout (`uvx --from .`) only → rejected; must support GitHub fetch.
  - Pinning to a fixed ref only → rejected; allow `<ref>` placeholder for consumers.

## Repository Touchpoints (expected)

- Root workspace config: `pyproject.toml` (uv workspace members and dev tools)
- Devcontainer: `.devcontainer/Dockerfile`, `.devcontainer/post-create.sh`, and devcontainer docs
- Tool docs: each `mcp-tools/<tool>/README.md` and any usage docs
- Root docs: `README.md` and removal-candidates report

## Open Questions

None required for planning. If the user’s unfinished “I am building with…” statement implies additional tooling constraints (e.g., a specific CI system or MCP client), capture them during implementation review and keep the plan aligned to the Constitution.
