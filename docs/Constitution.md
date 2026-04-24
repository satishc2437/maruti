# Maruti Constitution

This document is the living charter for the Maruti repository. It defines the
principles, engineering standards, and quality gates that govern every change.
It is written to be read by both humans and AI agents — the MUST/SHOULD
keywords carry their [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119)
meaning and are intended to be machine-assertable by tooling.

When a principle and a convenience practice disagree, the principle wins. When
this document and another doc in `docs/` disagree, this document wins — update
the other doc to match.

## Core Principles

### 1) Tool Isolation (MUST)
Each MCP tool MUST be a self-contained Python project.

- Tool code MUST NOT import, reference, or depend on code from sibling tool folders.
- Shared functionality MUST NOT be implemented as a shared internal library inside this repo.
	If true sharing is required, it MUST be promoted to a separately versioned external package.

Rationale: tools are intended to be independently runnable, releasable, and safe to change.

### 2) Tool-Local Source, Tests, Specs, and Docs (MUST)
Each tool folder MUST contain:

- its own `pyproject.toml`
- its own `mcp-tools/<package>/src/...`
- its own tests (`mcp-tools/<package>/tests/`)
- its own `specs/` directory (see `docs/specs-template.md`)
- its own `README.md`

Rationale: avoids monorepo coupling and makes each tool portable. When a tool
is installed via `uvx --from "git+...#subdirectory=mcp-tools/<tool>"`, its
spec, tests, and docs travel with it.

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
Development MUST follow TDD (red -> green -> refactor).

- Every tool MUST maintain ≥95% honest code coverage.
- Coverage MUST NOT be obtained by omitting files from measurement. In particular, `server.py`
	and `__main__.py` MUST be measured, not excluded.
- Tests MUST be meaningful (assert behavior and failure modes), not superficial.
- Test file names MUST describe the behavior they verify, not the metric they hit
	(i.e. `test_streaming_extraction.py`, not `test_more_coverage.py`).
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
The "UX" of these tools is the developer/agent experience.

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
- `specs/` MUST contain at least one spec document using the template at `docs/specs-template.md`.

## Development Workflow & Quality Gates

- Every change starts with a test (or a test update) that fails for the intended reason.
- Keep PRs small and tool-scoped.
- Required gates per tool (enforced by CI):
	- formatting checks
	- Python linting with zero errors
	- Pylint MUST report zero errors and zero warnings across in-scope Python code
	- docstring/documentation checks with zero docstring-specific warnings
	- unit tests
	- integration/contract tests when I/O boundaries exist
	- honest coverage ≥95%
- When adding a new tool:
	- ensure devcontainer auto-discovery picks it up
	- ensure it can run via `uv run <tool>` and via `uvx` from GitHub

Definition of Done (per tool):

- Tool runs in-container
- README includes working `uvx` snippet
- Lint passes with zero errors
- Pylint passes with zero errors and zero warnings
- Public APIs are documented (docstrings) and docstring checks pass with zero warnings
- Tests are comprehensive and honest coverage gate passes
- Performance constraints are documented and enforced where relevant

Canonical Pylint gate (repo-wide):

- Config MUST be sourced from `.pylintrc` at repo root.
- Run: `uv run pylint mcp-tools/*/src`.
- The command MUST exit 0 (no E/W/F messages).

## Agent Markdowns

This repository is also a factory for agent markdown definitions under
`agents/<name>/`. The `agents/` directory is the single source of truth; the
`.github/agents/` directory exists to make a subset of those agents available
to this repo's own Copilot and is populated via symlinks (see `scripts/link_agents.py`).

Agent markdowns SHOULD reference other agents generically (e.g. "a
spec-drafting subagent") rather than naming a specific external framework —
this keeps them portable across consuming environments.

## Amendments

Changes to this document MUST:

- state the motivation
- identify impacted tools (if any)
- include a migration plan if behavior or gates change

Compliance review expectations:

- MUST principles are enforced as hard gates where practical (CI-enforced).
- SHOULD principles are enforced via reviews/checklists and periodic quality work.
