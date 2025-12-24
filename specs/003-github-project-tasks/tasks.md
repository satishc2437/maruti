# Tasks: GitHub Project Task Queue

**Input**: Design documents from `specs/003-github-project-tasks/`
**Prerequisites**: `specs/003-github-project-tasks/plan.md`, `specs/003-github-project-tasks/spec.md`, `specs/003-github-project-tasks/research.md`, `specs/003-github-project-tasks/data-model.md`, `specs/003-github-project-tasks/contracts/mcp-contracts.json`

**Tests**: Tests are REQUIRED. This repo follows TDD and enforces per-tool coverage gates (>95%).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Baseline: run `uv run pytest -q` for mcp-tools/github-app-mcp (ref: mcp-tools/github-app-mcp/pyproject.toml)
- [X] T002 Baseline: run `uv run pylint mcp-tools/*/src` (repo gate) and record results in specs/003-github-project-tasks/quickstart.md
- [X] T003 [P] Add feature docs links in mcp-tools/github-app-mcp/README.md (reference specs/003-github-project-tasks/quickstart.md)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY project-task tool can be implemented safely.

- [X] T004 Add project allowlist config parsing for `GITHUB_APP_MCP_ALLOWED_PROJECTS` in mcp-tools/github-app-mcp/src/github_app_mcp/config.py
- [X] T005 Add policy support for allowed projects in mcp-tools/github-app-mcp/src/github_app_mcp/policy.py
- [X] T006 Add GraphQL client wrapper (POST `/graphql`, fixed documents, safe errors) in mcp-tools/github-app-mcp/src/github_app_mcp/github_graphql_client.py
- [X] T007 [P] Add GraphQL client unit tests (timeouts/retries/error mapping) in mcp-tools/github-app-mcp/tests/test_github_graphql_client.py
- [X] T008 Add runtime wiring for GraphQL client in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py
- [X] T009 [P] Update server status resource to include project allowlist enabled/count in mcp-tools/github-app-mcp/src/github_app_mcp/server.py
- [X] T010 [P] Add config/policy tests for project allowlist parsing and decisions in mcp-tools/github-app-mcp/tests/test_foundation_config.py

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Populate project from task list (Priority: P1) 🎯 MVP

**Goal**: Create Issues across multiple repos (full task object) and add each Issue as an item to a single allowlisted Project.

**Independent Test**: Using mocked GitHub APIs, an agent can create Issues in two different repos and successfully add both to the allowlisted Project; attempts against a disallowed repo/project are denied.

### Tests (TDD)

- [X] T011 [P] [US1] Add schema validation tests for `create_issue` inputs (labels/assignees/milestone) in mcp-tools/github-app-mcp/tests/test_contract_schemas.py
- [X] T012 [P] [US1] Add policy denial tests for disallowed project calls in mcp-tools/github-app-mcp/tests/test_policy.py
- [X] T052 [P] [US1/US2] Add repo allowlist denial tests for repo-scoped tools (`create_issue`, `get_issue`, `update_issue`) in mcp-tools/github-app-mcp/tests/test_policy.py (assert denial + `correlation_id`)
- [X] T013 [P] [US1] Add happy-path tests for issue creation (REST) in mcp-tools/github-app-mcp/tests/test_tools_happy_paths.py
- [X] T014 [P] [US1] Add happy-path tests for add-issue-to-project (GraphQL) in mcp-tools/github-app-mcp/tests/test_tools_happy_paths.py

### Implementation

- [X] T015 [US1] Add `create_issue` tool metadata + validation schema in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py
- [X] T016 [US1] Implement `create_issue` tool (REST: POST /repos/{owner}/{repo}/issues) in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py
- [X] T017 [US1] Add `get_project_v2_by_number` tool metadata + validation schema in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py
- [X] T018 [US1] Implement `get_project_v2_by_number` tool (GraphQL fixed query) in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py
- [X] T019 [US1] Add `add_issue_to_project_v2` tool metadata + validation schema in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py
- [X] T020 [US1] Implement `add_issue_to_project_v2` tool (GraphQL mutation using issue node id) in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py
- [X] T021 [US1] Add/extend payload size limits for `create_issue` body/title in mcp-tools/github-app-mcp/src/github_app_mcp/config.py
- [X] T022 [US1] Update allow-listed operation set to include US1 tools in mcp-tools/github-app-mcp/src/github_app_mcp/policy.py

**Checkpoint**: US1 is functional and independently testable.

---

## Phase 4: User Story 2 - Work tasks one-by-one from the project (Priority: P2)

**Goal**: List Project items, load a task’s Issue details, update Issue content/metadata/state, and move the task through a status workflow.

**Independent Test**: With mocked GitHub APIs, list items filtered by status, select one item, set status to In Progress, update Issue, then set status to Done and close the Issue.

### Tests (TDD)

- [X] T023 [P] [US2] Add schema validation tests for Project list/get/set tools in mcp-tools/github-app-mcp/tests/test_contract_schemas.py (incl. pagination bounds: `page_size` max 50 and clear validation error when exceeded)
- [X] T024 [P] [US2] Add happy-path tests for list/get project items and set status in mcp-tools/github-app-mcp/tests/test_tools_happy_paths.py
- [X] T025 [P] [US2] Add happy-path tests for get/update issue in mcp-tools/github-app-mcp/tests/test_tools_happy_paths.py (assert `get_issue` includes `issue_node_id` for chaining)

### Implementation

- [X] T026 [US2] Add `list_project_v2_fields` tool metadata + validation schema in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py
- [X] T027 [US2] Implement `list_project_v2_fields` tool (GraphQL fixed query incl. single-select options) in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py
- [X] T028 [US2] Add `list_project_v2_items` tool metadata + validation schema (pagination + optional status filter; enforce `page_size` default 20, max 50) in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py
- [X] T029 [US2] Implement `list_project_v2_items` tool (GraphQL query, bounded page size; reject `page_size` > 50 with validation error) in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py
- [X] T030 [US2] Add `get_project_v2_item` tool metadata + validation schema in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py
- [X] T031 [US2] Implement `get_project_v2_item` tool (GraphQL query returning item fields + linked issue identifiers) in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py
- [X] T032 [US2] Add `set_project_v2_item_field_value` tool metadata + validation schema in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py
- [X] T033 [US2] Implement `set_project_v2_item_field_value` tool (GraphQL mutation for single-select option id) in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py
- [X] T034 [US2] Add `get_issue` tool metadata + validation schema in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py
- [X] T035 [US2] Implement `get_issue` tool (REST: GET /repos/{owner}/{repo}/issues/{number}) in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py
- [X] T036 [US2] Add `update_issue` tool metadata + validation schema (title/body/labels/assignees/milestone/state) in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py
- [X] T037 [US2] Implement `update_issue` tool (REST: PATCH /repos/{owner}/{repo}/issues/{number}) in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py
- [X] T038 [US2] Update allow-listed operation set to include US2 tools in mcp-tools/github-app-mcp/src/github_app_mcp/policy.py

### Contracts (lock chaining early)

- [X] T051 [P] [US2] Update specs/003-github-project-tasks/contracts/mcp-contracts.json to fully describe US2 tools AND explicitly require `issue_node_id` in `create_issue` and `get_issue` outputs (chaining contract), plus any `list_project_v2_items` pagination fields.

**Checkpoint**: US2 is functional and independently testable.

---

## Phase 5: User Story 3 - Safe, allow-listed project access (Priority: P3)

**Goal**: Preserve safe-by-default behavior for all new Project tools: strict allowlist, secret-safe inputs, consistent auditing, stable envelopes.

**Independent Test**: Disallowed projects are denied; GraphQL errors are safely surfaced; every attempt emits exactly one audit event with a correlation id.

### Tests (TDD)

- [X] T039 [P] [US3] Add tests that project tools enforce allowlist (deny-by-default) in mcp-tools/github-app-mcp/tests/test_tools_policy_enforcement.py
- [X] T040 [P] [US3] Add tests that GraphQL tool failures still return `correlation_id` and are audited once in mcp-tools/github-app-mcp/tests/test_foundation_audit.py
- [X] T041 [P] [US3] Add secret-safety regression tests for new inputs (labels/assignees/body) in mcp-tools/github-app-mcp/tests/test_foundation_safety.py

### Implementation

- [X] T042 [US3] Enforce project allowlist checks inside dispatch/tool execution for project tools in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py
- [X] T043 [US3] Update README configuration docs to include `GITHUB_APP_MCP_ALLOWED_PROJECTS` in mcp-tools/github-app-mcp/README.md
- [X] T044 [US3] Update capabilities resource to mention project allowlist and GraphQL usage in mcp-tools/github-app-mcp/src/github_app_mcp/server.py

**Checkpoint**: US3 safety/policy/audit guarantees are verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T045 [P] Update allow-listed tools list in mcp-tools/github-app-mcp/README.md to include new project/issue tools
- [X] T046 [P] Verify spec contracts remain accurate after polish (if T051 was completed earlier, this should be a no-op review)
- [X] T047 Run full tool suite + coverage gate for mcp-tools/github-app-mcp (ref: mcp-tools/github-app-mcp/pyproject.toml) and ensure coverage stays >95%
- [X] T048 Run repo-wide lint gates (`uv run ruff check .`, `uv run pylint mcp-tools/*/src`) and resolve any new violations in mcp-tools/github-app-mcp/src/github_app_mcp/
- [X] T049 Validate quickstart steps remain accurate in specs/003-github-project-tasks/quickstart.md
- [X] T050 [P] Add a regression test or documented manual check to validate SC-001 (25 issues across 3 repos) in specs/003-github-project-tasks/quickstart.md

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → Phase 3+ (user stories) → Phase 6
- User story order for incremental delivery: **US1 (MVP)** → US2 → US3

### Dependency graph

```text
Phase 2 (Foundation)
	├─> US1 (Populate backlog)
	├─> US2 (Work backlog)
	└─> US3 (Safety/policy hardening)
```

## Parallel Execution Examples

### US1 parallel examples

- `T011` (schema tests) and `T012` (policy denial tests) can proceed in parallel across mcp-tools/github-app-mcp/tests/.
- `T015` (tool schema) and `T022` (policy allowlist update) can proceed in parallel in mcp-tools/github-app-mcp/src/github_app_mcp/.

### US2 parallel examples

- `T023` (schemas) and `T024`/`T025` (happy paths) can proceed in parallel in mcp-tools/github-app-mcp/tests/.

### US3 parallel examples

- `T039`–`T041` can proceed in parallel in mcp-tools/github-app-mcp/tests/.

## Implementation Strategy

- Implement **US1 only** first (MVP): create issue + add to project + resolve project.
- Then implement **US2** to enable queue-driven execution.
- Finish with **US3** enforcement hardening + documentation.
