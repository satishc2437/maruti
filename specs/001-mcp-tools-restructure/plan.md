# Implementation Plan: MCP Tools Restructure

**Branch**: `001-mcp-tools-restructure` | **Date**: 2025-12-21 | **Spec**: [specs/001-mcp-tools-restructure/spec.md](spec.md)
**Input**: Feature specification from `/specs/001-mcp-tools-restructure/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Restructure the repository to use a single top-level `mcp-tools/` directory containing the four in-scope MCP tools, keep each tool independently runnable, and update devcontainer + root + tool docs/configs to match the new layout. Produce a repo-root removal-candidates report but do not delete anything without explicit confirmation.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.14
**Primary Dependencies**: uv/uvx (workspace + execution), `mcp` (per-tool), standard Python packaging via `pyproject.toml`
**Storage**: N/A for this feature (no new data storage)
**Testing**: pytest (root convenience + per-tool tests)
**Target Platform**: Linux devcontainer (primary), general local developer machines via uv
**Project Type**: Tool monorepo (multiple independent Python projects)
**Performance Goals**: N/A for this feature (no new runtime behavior)
**Constraints**: No cross-tool imports; no deletions without explicit confirmation; docs must remain accurate
**Scale/Scope**: 4 tools migrated under `mcp-tools/` plus repo-level config + docs updates

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Source of truth: `.specify/memory/constitution.md`

Gates for this feature (MUST):

1. Tool Isolation: changes MUST NOT introduce cross-tool runtime dependencies.
2. Tool-Local Source/Tests/Docs: each tool keeps its own `pyproject.toml`, `src/`, tests, and README.
3. Devcontainer-First: devcontainer setup and scripts MUST reflect the new `mcp-tools/` layout.
4. Python 3.14 Standardization: in-scope tools and workspace MUST target Python 3.14.
5. uv/uvx Distribution Contract: each tool README includes a copy/paste `uvx` snippet (including GitHub `#subdirectory=mcp-tools/<tool>` pattern).
6. TDD + Coverage Gate: tests remain runnable; this feature should not reduce testability.

Status at plan time:

- Expected PASS: (1) Tool Isolation (structural), (2) Tool-Local structure (already in place)
- Needs verification during execution: (3) Devcontainer docs/scripts, (4) Python 3.14 everywhere, (5) uvx snippets in each README, (6) tests run cleanly post-move

Post-Phase 1 re-check (artifacts created):

- Phase 0 output exists: `research.md`
- Phase 1 outputs exist: `data-model.md`, `contracts/README.md`, `quickstart.md`
- Remaining work is execution/verification against the gates in repo source + docs

## Project Structure

### Documentation (this feature)

```text
specs/001-mcp-tools-restructure/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
.
├── mcp-tools/
│   ├── agent-memory/
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   ├── src/
│   │   └── tests/
│   ├── onenote-reader/
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   ├── src/
│   │   └── tests/
│   ├── pdf-reader/
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   ├── src/
│   │   └── tests/
│   └── xlsx-reader/
│       ├── pyproject.toml
│       ├── README.md
│       ├── src/
│       └── tests/
├── .devcontainer/
├── .specify/
├── specs/
├── pyproject.toml
└── README.md
```

**Structure Decision**: Tool monorepo: each tool remains a separate Python project under `mcp-tools/`, with a small root workspace used for devcontainer + shared dev tooling.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |

## Phase 0: Research (resolve uncertainties)

Deliverable: `specs/001-mcp-tools-restructure/research.md`

Research questions to resolve:

- Confirm the authoritative “standard stack” for this repo: Python 3.14 + uv/uvx + devcontainer (already strongly implied by constitution and existing `pyproject.toml`).
- Confirm the canonical `uvx` “from GitHub” invocation pattern for MCP clients (including `#subdirectory=mcp-tools/<tool>`).
- Identify the minimal set of repo files that must be updated to reflect the new layout (devcontainer scripts, workflow docs, root README, tool READMEs).

## Phase 1: Design & Contracts

Deliverables:

- `data-model.md`: N/A (no new persistent entities)
- `contracts/`: N/A for external APIs; include a note explaining why
- `quickstart.md`: Verification steps for reviewers (commands to validate structure, docs, and tests)

## Phase 2: Implementation Plan (work breakdown)

Execution order (high-level):

1. Confirm/ensure tool directories are under `mcp-tools/` (no top-level tool dirs remain).
2. Update root workspace config (`pyproject.toml` workspace members; root dev dependencies for tests).
3. Update devcontainer scripts/docs to discover tools under `mcp-tools/*/` and keep Python 3.14 alignment.
4. Update tool docs for path changes and required `uvx` snippets.
5. Create/update root `README.md`.
6. Generate repo-root removal-candidates report (flag only).
7. Run sanity checks (`uv sync --dev`, `uv run pytest`) and fix only migration-caused issues.
