# Implementation Plan: GitHub Project Task Queue

**Branch**: `003-github-project-tasks` | **Date**: 2025-12-23 | **Spec**: [specs/003-github-project-tasks/spec.md](specs/003-github-project-tasks/spec.md)
**Input**: Feature specification from `specs/003-github-project-tasks/spec.md`

## Summary

Add a minimal, allow-listed set of MCP operations to let an agent (using a GitHub App identity) create Issues across many allowlisted repositories, add them into a single allowlisted GitHub Project (Projects v2), then fetch tasks from that Project and progress them one-by-one by updating a single-select status field.

Projects v2 operations are implemented via a dedicated, fixed-query GraphQL client; Issue operations are implemented via the existing REST client. All new operations preserve the existing policy/audit/secret-safety guarantees.

## Technical Context

**Language/Version**: Python 3.14
**Primary Dependencies**: `mcp`, `httpx`, `PyJWT`, `cryptography`
**Storage**: Optional JSONL audit file sink (host-provided absolute path); otherwise stderr/logging
**Testing**: `pytest`, `pytest-asyncio`, `pytest-cov`
**Target Platform**: Linux devcontainer; MCP stdio server
**Project Type**: Tool monorepo (this repo), target tool: `mcp-tools/github-app-mcp`
**Performance Goals**: Interactive agent workflows; bounded pagination; avoid unbounded enumeration
**Constraints**:
- No arbitrary GitHub API passthrough
- Network egress restricted to `https://api.github.com` (plus GraphQL at `https://api.github.com/graphql`)
- Never return secrets (tokens/private keys/installation ids)
- Tool responses include `correlation_id` and emit exactly one audit event per attempt
**Scale/Scope**:
- Single project used as the task queue
- Many repos allowed; tasks represented as Issues
- Pagination required for project items; default page sizes should be small and bounded

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Applicable constitution requirements (summary):

- Tool isolation preserved (changes confined to `mcp-tools/github-app-mcp`)
- Python 3.14 maintained
- uv/uvx distribution contract preserved
- TDD + coverage >95% preserved for `github-app-mcp`
- Pylint must have zero errors and zero warnings repo-wide

Required gates for this feature:

- `uv run ruff check .` (docstring rules are enabled repo-wide)
- `uv run pylint mcp-tools/*/src` (must exit 0)
- `cd mcp-tools/github-app-mcp && uv run pytest -q` (coverage gate `fail_under = 95` must pass)

**Gate evaluation (pre-research)**: PASS (plan does not introduce any required violations)

## Project Structure

### Documentation (this feature)

```text
specs/003-github-project-tasks/
 plan.md
 research.md
 data-model.md
 quickstart.md
 contracts/
 tasks.md
```

### Source Code (repository root)

```text
mcp-tools/github-app-mcp/
 pyproject.toml
 README.md
 src/
   └── github_app_mcp/
       ├── config.py
       ├── policy.py
       ├── github_client.py
       ├── tools.py
       └── ...
 tests/
```

**Structure Decision**: Implement all changes within the existing `github-app-mcp` tool project.

## Phase 0: Outline & Research

Outputs:

- [specs/003-github-project-tasks/research.md](research.md)

Key decisions captured:

- Projects v2 via fixed-query GraphQL client
- Explicit project allowlist (`GITHUB_APP_MCP_ALLOWED_PROJECTS`)
- Minimal tool surface only (no project CRUD)
- “Full task object” support via standard Issue fields (labels/assignees/milestone)

## Phase 1: Design & Contracts

Outputs:

- [specs/003-github-project-tasks/data-model.md](data-model.md)
- [specs/003-github-project-tasks/contracts/mcp-contracts.json](contracts/mcp-contracts.json)
- [specs/003-github-project-tasks/quickstart.md](quickstart.md)

Design notes (what will be implemented):

- Add new tools to `TOOL_METADATA` and `ALLOW_LISTED_OPERATIONS`:
  - `get_project_v2_by_number`
  - `list_project_v2_fields`
  - `list_project_v2_items`
  - `get_project_v2_item`
  - `set_project_v2_item_field_value` (single-select option id)
  - `add_issue_to_project_v2`
  - `create_issue`, `get_issue`, `update_issue`
- Add new policy config + enforcement for project allowlist.
  - Enforcement is intentional “two layers”:
    - policy layer: deny-by-default decisioning for project identifiers
    - tool execution layer: project tools must call the policy gate before issuing GraphQL requests (defense-in-depth)
- Add GraphQL client wrapper with the same safety constraints as REST (fixed host, no redirects, bounded retries/timeouts, safe errors).
- Update capabilities/server-status to disclose whether project allowlist is enabled (counts only; no secrets).

**Constitution re-check (post-design)**: PASS (no new violations introduced)

## Phase 2: Implementation Planning (Tasks)

This phase produces `specs/003-github-project-tasks/tasks.md` via `/speckit.tasks` and is intentionally not generated by `/speckit.plan`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
