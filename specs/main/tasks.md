---
description: "Tasks to add docstrings across the repo and enforce zero docstring-specific warnings"
---

# Tasks: Repo-Wide Docstrings & Docstring-Lint Gate

**Input**: Design documents from `/specs/main/`
**Prerequisites**: plan.md (required), spec.md (required)

**Tests**: No new functional tests are expected for this documentation-only change; existing tests + coverage gates must continue to pass, and docstring checks act as the primary added gate.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add a docstring-specific lint gate and make it runnable in-container.

- [x] T001 Add `ruff` to root dev dependencies in pyproject.toml
- [x] T002 [P] Add `ruff` to pdf-reader dev deps in mcp-tools/pdf-reader/pyproject.toml
- [x] T003 [P] Add `ruff` to agent-memory dev deps in mcp-tools/agent-memory/pyproject.toml
- [x] T004 [P] Add `ruff` to onenote-reader dev deps in mcp-tools/onenote-reader/pyproject.toml
- [x] T005 [P] Add `ruff` to xlsx-reader dev deps in mcp-tools/xlsx-reader/pyproject.toml

- [x] T006 Configure root ruff docstring rules in pyproject.toml (`[tool.ruff]` + `[tool.ruff.lint]` selecting `D` rules; set `pydocstyle.convention = "google"`; exclude: `**/tests/**`, `.specify/**`, `**/__pycache__/**`. Scope is enforced by the CLI paths: `main.py` + `mcp-tools/*/src/**`.)
- [x] T007 [P] (Optional) Configure ruff docstring rules in mcp-tools/agent-memory/pyproject.toml only if needed to run `ruff` from that tool directory; MUST mirror root docstring settings
- [x] T008 [P] (Optional) Configure ruff docstring rules in mcp-tools/onenote-reader/pyproject.toml only if needed to run `ruff` from that tool directory; MUST mirror root docstring settings
- [x] T009 [P] (Optional) Configure ruff docstring rules in mcp-tools/pdf-reader/pyproject.toml only if needed to run `ruff` from that tool directory; MUST mirror root docstring settings
- [x] T010 [P] (Optional) Configure ruff docstring rules in mcp-tools/xlsx-reader/pyproject.toml only if needed to run `ruff` from that tool directory; MUST mirror root docstring settings

**Checkpoint**: `uv run ruff check --select D main.py mcp-tools/*/src` (or the documented equivalent) runs and reports docstring issues (expected at first).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Define repo-wide documentation expectations and a repeatable command.


- [x] T011 Document the docstring check command in README.md (root) and define expected scope (e.g., `src/**` + tool packages; whether `tests/**` are excluded) (Preserve/verify the existing `uvx` snippet remains present and copy/pasteable.)
- [x] T012 [P] Document the docstring check command in mcp-tools/agent-memory/README.md (Preserve/verify the existing `uvx` snippet remains present and copy/pasteable.)
- [x] T013 [P] Document the docstring check command in mcp-tools/onenote-reader/README.md (Preserve/verify the existing `uvx` snippet remains present and copy/pasteable.)
- [x] T014 [P] Document the docstring check command in mcp-tools/pdf-reader/README.md (Preserve/verify the existing `uvx` snippet remains present and copy/pasteable.)
- [x] T015 [P] Document the docstring check command in mcp-tools/xlsx-reader/README.md (Preserve/verify the existing `uvx` snippet remains present and copy/pasteable.)


**Checkpoint**: A contributor can run the documented command(s) in-container and reproduce docstring results deterministically.
**Checkpoint**: README edits preserve the constitution-required `uvx` snippet(s) and do not make them less copy/pasteable.

---

## Phase 3: User Story 1 - Docstrings for Public APIs (Priority: P1)

**Goal**: Public Python APIs across the repo have clear docstrings and docstring lint has zero warnings.

**Independent Test**: Run `uv run ruff check --select D main.py mcp-tools/*/src` and confirm it reports 0 docstring warnings.

- [x] T016 [P] [US1] Add/upgrade module docstrings and public API docstrings in mcp-tools/agent-memory/src/agent_memory/{__init__.py,__main__.py,errors.py,memory_ops.py,safety.py,server.py,tools.py}
- [x] T017 [P] [US1] Add/upgrade module docstrings and public API docstrings in mcp-tools/onenote-reader/src/onenote_reader/{__init__.py,__main__.py,auth.py,config.py,errors.py,graph_client.py,safety.py,server.py,tools.py}
- [x] T018 [P] [US1] Add/upgrade module docstrings and public API docstrings in mcp-tools/pdf-reader/src/pdf_reader/{__init__.py,__main__.py,errors.py,pdf_processor.py,safety.py,server.py,tools.py}
- [x] T019 [P] [US1] Add/upgrade module docstrings and public API docstrings in mcp-tools/xlsx-reader/src/xlsx_reader/{__init__.py,__main__.py,errors.py,safety.py,server.py}
- [x] T020 [P] [US1] Add/upgrade docstrings in mcp-tools/xlsx-reader/src/xlsx_reader/processors/{workbook.py,charts.py,exporters.py,pivots.py,__init__.py}
- [x] T021 [P] [US1] Add/upgrade docstrings in mcp-tools/xlsx-reader/src/xlsx_reader/utils/{validation.py,__init__.py} and mcp-tools/xlsx-reader/src/xlsx_reader/tools/{__init__.py}
- [x] T022 [US1] Add/upgrade docstrings for any root-level Python entrypoints (main.py) and ensure they are within docstring-lint scope
- [x] T023 [US1] Run docstring lint and fix remaining issues (preferred: add docstrings; allowed: narrowly-scoped per-file ignores with justification in pyproject.toml)

**Checkpoint**: Docstring lint is clean and key tool entrypoints are self-explanatory from docstrings.

---

## Phase 4: User Story 2 - Enforced Docstring Gate (Priority: P2)

**Goal**: Docstring checks are easy to run and prevent regressions.

**Independent Test**: A contributor can run the documented docstring command(s) and observe a failing exit code if a docstring rule is violated.

- [x] T024 [P] [US2] Add a documented “Docstring checks” section to MCP_DEVELOPMENT_WORKFLOW.md (repo root) including the exact `uv run ruff ...` command
- [x] T025 [US2] Add a simple “quality gates” snippet to each tool README pointing to the docstring check command and the “zero warnings” requirement (mcp-tools/*/README.md)

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Ensure everything stays green and documentation changes are consistent.

- [x] T026 [P] Run `uv sync --dev --all-packages` and confirm dependencies are consistent after adding `ruff`
- [x] T027 [P] Run per-tool coverage gates (e.g., `cd mcp-tools/<tool> && uv run pytest --cov --cov-fail-under=95`) and confirm all tools remain >=95%
- [x] T028 Run `uv run pytest -q` from repo root and confirm all tests still pass
- [x] T029 Run `uv run ruff check --select D main.py mcp-tools/*/src` and confirm zero docstring warnings across the agreed scope

---

## Dependencies & Execution Order

- Phase 1 (Setup) blocks everything else (need a runnable docstring check first).
- Phase 2 (Foundational) blocks story work only to the extent that the scope/convention must be agreed before bulk edits.
- Phase 3 (US1) can be parallelized by tool/package.
- Phase 4 (US2) can run in parallel with Phase 3 once Phase 2 establishes the canonical command.
- Phase 5 validates the overall result.

## Parallel Execution Examples

**US1 parallelization (by tool package):**

- Agent Memory: T016
- OneNote Reader: T017
- PDF Reader: T018
- XLSX Reader (core): T019
- XLSX Reader (processors/utils): T020, T021

**Setup parallelization (by tool):**

- Add `ruff` to tool dev deps: T002–T005
- Add tool-local ruff config: T007–T010
