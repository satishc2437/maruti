# Tasks: MCP Tools Restructure

**Input**: Design documents from `/specs/001-mcp-tools-restructure/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are REQUIRED. This repo follows TDD and enforces per-tool coverage gates (>95%).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Ensure the workspace is in a consistent, reviewable state before any story-specific work.

- [x] T001 Confirm the feature branch is checked out and specs exist in specs/001-mcp-tools-restructure/spec.md
- [x] T002 Confirm tool directories exist under mcp-tools/ (mcp-tools/agent-memory, mcp-tools/onenote-reader, mcp-tools/pdf-reader, mcp-tools/xlsx-reader) AND that old top-level tool directories do not exist at repo root (agent-memory/, onenote-reader/, pdf-reader/, xlsx-reader/)
- [x] T003 Confirm root README exists and is linked from pyproject.toml (`README.md` and `pyproject.toml`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Repo-level configuration and dev-environment alignment that must be correct before doc verification and test runs are meaningful.

**⚠️ CRITICAL**: No user story work should be considered “done” until this phase is complete.

- [x] T004 Verify uv workspace members reference mcp-tools/* in pyproject.toml
- [x] T005 Verify root dev test tooling is present in pyproject.toml ([dependency-groups].dev includes pytest/pytest-asyncio/pytest-cov)
- [x] T006 [P] Update devcontainer build caching inputs to include all tool pyproject.toml files in .devcontainer/Dockerfile
- [x] T007 [P] Verify devcontainer post-create install/discovery loops over mcp-tools/*/ in .devcontainer/post-create.sh
- [x] T008 [P] Verify MCP tool creation script targets mcp-tools/<name>/ in .devcontainer/add-mcp-server.sh
- [x] T009 [P] Verify devcontainer docs reference Python 3.14 and mcp-tools/* paths in .devcontainer/README.md
- [x] T010 [P] Verify devcontainer quickstart references mcp-tools/* paths in .devcontainer/QUICKSTART.md

**Checkpoint**: Repo configuration and devcontainer docs/scripts are aligned to the new layout.

---

## Phase 3: User Story 1 - Use Tools From New Layout (Priority: P1) 🎯 MVP

**Goal**: Contributors can find and run each tool from the new `mcp-tools/` layout with accurate docs.

**Independent Test**: A reviewer can (a) list the `mcp-tools/` directory and see all tools, and (b) follow each tool’s README “Run” instructions without encountering old paths.

### Implementation (Docs + Repo references)

- [x] T011 [P] [US1] Update any remaining repo docs referencing old tool root paths in MCP_DEVELOPMENT_WORKFLOW.md
- [x] T012 [P] [US1] Ensure agent-memory docs reference mcp-tools/ paths in mcp-tools/agent-memory/README.md
- [x] T013 [P] [US1] Ensure agent-memory troubleshooting docs reference mcp-tools/ paths in mcp-tools/agent-memory/TROUBLESHOOTING.md
- [x] T014 [P] [US1] Ensure pdf-reader docs reference mcp-tools/ paths and include uvx GitHub snippet in mcp-tools/pdf-reader/README.md
- [x] T015 [P] [US1] Ensure pdf-reader usage docs reference mcp-tools/ paths and include uvx GitHub snippet in mcp-tools/pdf-reader/MCP_USAGE.md
- [x] T016 [P] [US1] Ensure xlsx-reader docs reference mcp-tools/ paths and include uvx GitHub snippet in mcp-tools/xlsx-reader/README.md
- [x] T017 [P] [US1] Ensure xlsx-reader usage docs reference mcp-tools/ paths and include uvx GitHub snippet in mcp-tools/xlsx-reader/USAGE_EXAMPLES.md
- [x] T018 [P] [US1] Ensure onenote-reader docs reference mcp-tools/ paths and include uvx GitHub snippet in mcp-tools/onenote-reader/README.md

### Verification

- [x] T019 [US1] Repo-wide search to confirm no maintained docs instruct old root tool paths (update files found; likely targets README.md, MCP_DEVELOPMENT_WORKFLOW.md, .devcontainer/*, mcp-tools/*)
  - Scope (maintained docs): README.md, MCP_DEVELOPMENT_WORKFLOW.md, .devcontainer/**/*.md, and these tool docs:
    - mcp-tools/*/README.md
    - mcp-tools/*/MCP_USAGE.md
    - mcp-tools/*/USAGE_EXAMPLES.md
    - mcp-tools/*/TROUBLESHOOTING.md
  - Check (examples): search for old path patterns like `cd pdf-reader`, `cd xlsx-reader`, `cd onenote-reader`, `cd agent-memory` and update them to `cd mcp-tools/<tool>`.

**Checkpoint**: Docs consistently reference the `mcp-tools/<tool>/` layout.

---

## Phase 4: User Story 2 - Dev Environment Still Works (Priority: P2)

**Goal**: Devcontainer onboarding and tool discovery/install behavior matches the new layout.

**Independent Test**: A reviewer can read devcontainer docs and see correct paths, and can run the workspace setup commands without path errors.

### Implementation

- [x] T020 [US2] Verify devcontainer Dockerfile installs workspace deps and then installs MCP tools from mcp-tools/* in .devcontainer/Dockerfile
- [x] T021 [US2] Verify post-create aliases reference the new mcp-tools paths for targeted tests in .devcontainer/post-create.sh
- [x] T022 [US2] Verify workspace-level commands in README.md match uv/uvx and mcp-tools layout in README.md

### Verification (tests)

- [x] T023 [US2] Run `uv sync --dev` at repo root and confirm it succeeds (pyproject.toml)
- [x] T024 [US2] Smoke test: run `uv sync --dev --all-packages` (ensures all workspace members are installed for root test discovery/imports), then run `uv run pytest -q` at repo root and record/fix any failures caused by the restructure (scope-limited fixes in mcp-tools/* and pyproject.toml)

**Checkpoint**: Basic setup + tests run cleanly after restructure.

---

## Phase 5: User Story 3 - Root Cleanup Is Safe and Reviewable (Priority: P3)

**Goal**: Maintainers have a clear, reviewable list of removal candidates without any accidental deletions.

**Independent Test**: A reviewer can open the report and see a clear list + an explicit statement that nothing is deleted without confirmation.

### Implementation

- [x] T025 [US3] Create or update a repo-root removal candidates report in REMOVAL_CANDIDATES.md (flag only; do not delete)
- [x] T026 [US3] Ensure the repo-root README links to the removal candidates report and states deletion requires confirmation in README.md

### Verification

- [x] T027 [US3] Confirm git diff contains no “cleanup-only” deletions of repo-root files (review changes impacting REMOVAL_CANDIDATES.md and README.md)

**Checkpoint**: Cleanup is documented and safe.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final consistency sweep and validation against the Constitution gates.

- [x] T028 [P] Sweep for remaining Python version mentions that contradict 3.14 and update docs/configs found (README.md, .devcontainer/*, mcp-tools/*)
- [x] T029 [P] Verify each tool’s requires-python is >=3.14 and classifiers align in mcp-tools/*/pyproject.toml
- [x] T030 Verify each tool README contains a copy/paste `uvx` GitHub snippet using `#subdirectory=mcp-tools/<tool>` (mcp-tools/*/README.md)
- [x] T031 Run the quickstart verification steps and update them if reality diverges in specs/001-mcp-tools-restructure/quickstart.md
- [x] T032 Final verification: run full repo test suite after migration and fix any failures caused by restructure (run `uv run pytest` from repo root; apply fixes in mcp-tools/* and pyproject.toml)
- [x] T033 [P] Ensure `pytest-cov` is available for per-tool test runs (either via each tool’s dev deps in mcp-tools/*/pyproject.toml or via the workspace/devcontainer install)
- [x] T034 Run per-tool coverage gates (>95%) and fix any coverage regressions introduced by the restructure:
  - `cd mcp-tools/agent-memory && uv run pytest --cov=agent_memory --cov-fail-under=95`
  - `cd mcp-tools/onenote-reader && uv run pytest --cov=onenote_reader --cov-fail-under=95`
  - `cd mcp-tools/pdf-reader && uv run pytest --cov=pdf_reader --cov-fail-under=95`
  - `cd mcp-tools/xlsx-reader && uv run pytest --cov=xlsx_reader --cov-fail-under=95`
- [x] T035 Verify Tool Isolation: ensure no tool imports another tool’s package (e.g., search for cross-tool imports among `agent_memory`, `onenote_reader`, `pdf_reader`, `xlsx_reader` outside their own tool folder; fix any found by removing the dependency)
  - Check (mechanical): in each tool, ensure there are no `import <other_package>` or `from <other_package> import ...` usages in `mcp-tools/<tool>/src/**.py`.
  - Pass criteria: no cross-tool imports found in `src/` for any tool (tests may import their own tool package only).


---

## Dependencies & Execution Order

### User Story Completion Order (Dependency Graph)

- **US1 (P1)** → **US2 (P2)** and **US3 (P3)**
  - Rationale: layout + doc correctness (US1) is a prerequisite for validating devcontainer onboarding (US2) and for accurately flagging repo-root cleanup candidates (US3).

### Phase Dependencies

- **Phase 1 (Setup)** blocks nothing but prevents avoidable churn.
- **Phase 2 (Foundational)** blocks all user story validation.
- **Phase 3 (US1)** should be completed before deep verification steps.
- **Phase 4 (US2)** depends on Phase 2 and benefits from US1 being correct.
- **Phase 5 (US3)** can be done after Phase 2 (and ideally after US1 to avoid listing moved/renamed items incorrectly).
- **Phase 6 (Polish)** runs last.

---

## Parallel Execution Examples

### Parallel Example: US1

- Run in parallel:
  - T012 (agent-memory README) + T014 (pdf-reader README) + T016 (xlsx-reader README) + T018 (onenote-reader README)
  - T013 (agent-memory troubleshooting) + T015 (pdf-reader usage) + T017 (xlsx usage)

### Parallel Example: Foundational

- Run in parallel:
  - T006 (.devcontainer/Dockerfile) + T007 (.devcontainer/post-create.sh) + T008 (.devcontainer/add-mcp-server.sh)
  - T009 (.devcontainer/README.md) + T010 (.devcontainer/QUICKSTART.md)

### Parallel Example: Polish

- Run in parallel:
  - T028 (docs sweep) + T029 (pyproject consistency)

---

## Implementation Strategy

### MVP First (US1)

1. Complete Phase 1 + Phase 2
2. Implement US1 (docs + layout verification)
3. Run US1 verification (T019)

### Incremental Delivery

1. US1 → validate layout + docs
2. US2 → validate devcontainer + root tests
3. US3 → produce safe removal candidates report
4. Polish → final sweep + quickstart validation
