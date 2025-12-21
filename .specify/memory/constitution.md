<!--
Sync Impact Report
- Version change: TEMPLATE 3.14.0
- Modified principles: N/A (initial constitution)
- Added sections:
	- Core Principles expanded to 10 principles
	- Engineering Standards & Repository Constraints
	- Development Workflow & Quality Gates
- Removed sections: None
- Templates requiring updates:
	-  updated: .specify/templates/tasks-template.md
	-  updated: .specify/templates/plan-template.md
	-  no change: .specify/templates/spec-template.md
- Follow-up TODOs:
	- TODO(RATIFICATION_DATE): set once first ratified
	- Align all tool folders + devcontainer to Python 3.14 (repo currently contains mixed versions)
-->

# Maruti Constitution

## Core Principles

### 1) Tool Isolation (MUST)
Each MCP tool MUST be a self-contained Python project.

- Tool code MUST NOT import, reference, or depend on code from sibling tool folders.
- Shared functionality MUST NOT be implemented as a shared internal library inside this repo.
	If true sharing is required, it MUST be promoted to a separately versioned external package.

Rationale: tools are intended to be independently runnable, releasable, and safe to change.

### 2) Tool-Local Source, Tests, and Docs (MUST)
Each tool folder MUST contain:

- its own `pyproject.toml`
- its own `src/<package>/...`
- its own tests (prefer `tests/`)
- its own `README.md`

Rationale: avoids monorepo coupling and makes each tool portable.

### 3) Devcontainer-First Development (MUST)
All development MUST work inside the repository dev container.

- No undocumented host-only steps.
- Tool creation, installation, execution, linting, and testing MUST succeed in-container.

Rationale: eliminates environment drift and ensures repeatable builds.

### 4) Python 3.14 Standardization (MUST)
Python 3.14 is the repo standard.

- New tools MUST declare Python 3.14 support via `requires-python`.
- Existing tools MUST be migrated to Python 3.14 in a planned, deliberate manner.
- Tools MUST NOT rely on unspecified interpreter behavior.

Rationale: consistent language features and predictable tooling behavior.

### 5) uv/uvx as the Distribution Contract (MUST)
Tools MUST be installable and runnable via uv.

- Each tool README MUST include a copy/paste snippet suitable for `mcp.json` that uses `uvx`
	to fetch and run the tool directly from GitHub (no manual checkout required).
- The snippet MUST specify the tool entrypoint (`python -m <package>` or console script).

Rationale: frictionless adoption and consistent execution.

### 6) Test-Driven Development + Coverage Gate (MUST)
Development MUST follow TDD (red  green  refactor).

- Every tool MUST maintain >95% code coverage.
- Tests MUST be meaningful (assert behavior and failure modes), not superficial.
- Coverage requirements apply per tool; regressions block merges.

Rationale: correctness and safe refactoring across many unrelated tools.

### 7) Stable MCP Interfaces (SHOULD)
Treat tool names, parameters, and outputs as a public contract.

- Prefer backward-compatible changes.
- If breaking changes are necessary, document them and provide migration guidance.

Rationale: MCP clients and user workflows depend on stability.

### 8) Safe-by-Default File and Network Access (SHOULD)
Tools SHOULD default to least-privilege behavior.

- Validate inputs, prevent path traversal, enforce size/time limits.
- Avoid accidental secret disclosure in logs and errors.

Rationale: MCP tools often operate on user machines with sensitive data.

### 9) Performance is a Feature (SHOULD)
Performance requirements SHOULD be explicit for any tool that processes large inputs.

- Prefer streaming/iterative processing.
- Avoid unbounded memory growth.
- Add lightweight performance regression checks for critical paths.

Rationale: tools must remain responsive and reliable under real workloads.

### 10) Consistent Developer Experience (SHOULD)
The “UX” of these tools is the developer/agent experience.

- Consistent README structure across tools.
- Consistent error taxonomy and actionable messages.
- Consistent logging strategy (structured, safe by default).

Rationale: a toolbox repo is only valuable if tools are easy to understand and integrate.

## Engineering Standards & Repository Constraints

- Each tool is a separate Python project with its own dependency set.
- Tool code MUST NOT reference other tools.
- Each tool MUST define a clear, minimal public surface:
	- MCP tools/resources exposed
	- input validation rules
	- output schema guarantees
- Prefer deterministic, testable behavior over cleverness.
- Prefer standard library where practical; justify heavy dependencies.

Documentation requirements per tool:

- `README.md` MUST describe: purpose, features, safety limits, usage examples.
- `README.md` MUST include an `uvx` snippet that fetches from GitHub (no explicit download).
	(Exact syntax depends on the client; it must be copy/pasteable and verified.)

## Development Workflow & Quality Gates

- Every change starts with a test (or a test update) that fails for the intended reason.
- Keep PRs small and tool-scoped.
- Required gates per tool:
	- formatting + linting checks
	- unit tests
	- integration/contract tests when I/O boundaries exist
	- coverage >95%
- When adding a new tool:
	- ensure devcontainer auto-discovery picks it up
	- ensure it can run via `uv run <tool>` and via `uvx` from GitHub

Definition of Done (per tool):

- Tool runs in-container
- README includes working `uvx` snippet
- Tests are comprehensive and coverage gate passes
- Performance constraints are documented and enforced where relevant

## Governance

- This constitution governs development in this repo and supersedes convenience practices.
- Pull requests and reviews MUST verify constitution compliance for the affected tool(s).
- Amendments MUST:
	- state the motivation
	- identify impacted tools
	- include a migration plan if behavior or gates change
- Versioning policy for this constitution:
	- MAJOR: remove/redefine MUST principles or materially weaken gates
	- MINOR: add new principles/sections or materially expand guidance
	- PATCH: clarifications and non-semantic refinements

Compliance review expectations:

- MUST principles are enforced as hard gates where practical.
- SHOULD principles are enforced via reviews/checklists and periodic quality work.

**Version**: 3.14.0 | **Ratified**: TODO(RATIFICATION_DATE): set when first ratified | **Last Amended**: 2025-12-21
