# Implementation Plan: github-app-mcp

**Branch**: `002-github-app-mcp` | **Date**: 2025-12-22 | **Spec**: [specs/002-github-app-mcp/spec.md](spec.md)
**Input**: Feature specification from `/specs/002-github-app-mcp/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Create a new MCP tool `github-app-mcp` that enables AI agents to perform a strictly allow-listed set of GitHub operations using only a GitHub App identity. The server owns authentication (App JWT → installation token), enforces authorization/policy guardrails (repo allowlist, PR-only workflows, protected-branch constraints), produces enterprise-grade audit logs, and keeps all secrets (private key, tokens, installation details) opaque to agents.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.14
**Primary Dependencies**: `mcp` (stdio MCP server), `httpx` (GitHub REST calls), `PyJWT` + `cryptography` (GitHub App JWT signing)
**Storage**: Local audit log sink (JSON lines to stderr and/or optional file); no database
**Testing**: pytest, pytest-asyncio, pytest-cov
**Target Platform**: Linux devcontainer (primary); runnable via uv/uvx on developer machines
**Project Type**: Tool monorepo (new independent tool under `mcp-tools/`)
**Performance Goals**: Human-scale GitHub automation; keep operations responsive (typical operations complete in seconds) and avoid unbounded memory usage for large file payloads
**Constraints**: Secrets must never be returned to the agent; network access limited to GitHub API; enforce allow-lists and policy; deny unsupported operations; safe error messages; audit everything
**Scale/Scope**: One MCP server instance per configured GitHub App; operations limited to the app’s installed repositories and granted permissions, optionally narrowed by a server-side allowlist

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Source of truth: `.specify/memory/constitution.md`

Gates for this feature (MUST):

1. Tool Isolation: `github-app-mcp` MUST be a self-contained Python project and MUST NOT import code from sibling tool folders.
2. Tool-Local Source/Tests/Docs: `mcp-tools/github-app-mcp/` MUST include its own `pyproject.toml`, `src/`, tests, and `README.md`.
3. Devcontainer-First: tool development, linting, and testing MUST succeed in-container.
4. Python 3.14 Standardization: tool MUST declare `requires-python = ">=3.14"`.
5. uv/uvx Distribution Contract: tool README MUST include a copy/paste `uvx` snippet that runs from GitHub via `#subdirectory=mcp-tools/github-app-mcp`.
6. TDD + Coverage Gate: tool must maintain >95% coverage with meaningful tests.
7. Stable MCP Interfaces: tool names/inputs/outputs must be treated as a public contract.
8. Safe-by-Default File/Network Access: secrets must not leak via logs/errors; validate inputs; enforce size/time limits and a GitHub API host allowlist.

Repo quality gate (canonical):

- Pylint MUST report zero errors and zero warnings: `uv run pylint mcp-tools/*/src`.

## Project Structure

### Documentation (this feature)

```text
specs/002-github-app-mcp/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
```text
.
├── mcp-tools/
│   └── github-app-mcp/
│       ├── pyproject.toml
│       ├── README.md
│       ├── src/
│       │   └── github_app_mcp/
│       │       ├── __init__.py
│       │       ├── __main__.py
│       │       ├── github_client.py
│       │       ├── server.py
│       │       ├── tools.py
│       │       ├── auth.py
│       │       ├── config.py
│       │       ├── policy.py
│       │       ├── audit.py
│       │       ├── safety.py
│       │       └── errors.py
│       └── tests/
├── .specify/
├── specs/
└── pyproject.toml
```

**Structure Decision**: Tool monorepo. `github-app-mcp` is an independent Python project under `mcp-tools/`, matching existing tools.

## Complexity Tracking

No constitution violations are expected for this feature.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |

## Phase 0: Research (resolve uncertainties)

Deliverable: `specs/002-github-app-mcp/research.md`

Research questions to resolve:

- GitHub API approach for committing multiple file changes into a single commit (Contents API vs Git Data API) while keeping payload limits and error modes explicit.
- How to enforce “PR-only workflow” without relying on privileged branch-protection APIs (config-driven enforcement + best-effort branch-protection detection).
- Minimal dependency set that supports GitHub App auth (JWT signing) and async GitHub API calls.
- Audit log design that is useful for enterprise traceability without leaking secrets or file contents.
- Rate limiting/retry strategy for GitHub API and how to surface errors safely.

## Phase 1: Design & Contracts

Deliverables:

- `data-model.md`: Defines request/policy/audit entities and validation rules.
- `contracts/`: MCP tool contract documentation (allow-listed tool names, input schemas, output guarantees).
- `quickstart.md`: Reviewer-oriented setup and validation steps (in-container).

## Phase 2: Implementation Plan (work breakdown)

Execution order (high-level):

1. Create new tool project under `mcp-tools/github-app-mcp/` (pyproject, src layout, tests, README).
2. Implement configuration loading with host-provided env vars (including `.pem` path) and strict redaction.
3. Implement GitHub App auth: JWT creation, installation token exchange, safe caching with expiry.
4. Implement policy module: repo allowlist, PR-only workflow, protected branch restrictions, operation allowlist.
5. Implement MCP tools with typed schemas and deterministic outputs; reject unsupported intents.
6. Implement audit logging: JSON lines, correlation IDs, outcome logging (allowed/denied/failed) without secret content.
7. Add unit/integration tests for auth caching, policy decisions, tool schema validation, and redaction; maintain >95% coverage.
8. Verify constitution gates: `uv run pylint mcp-tools/*/src`, tests, and docs (README includes uvx snippet).
