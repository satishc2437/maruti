---

description: "Tasks for implementing github-app-mcp"

---

# Tasks: github-app-mcp

**Input**: Design documents from `/specs/002-github-app-mcp/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED. This repo follows TDD and enforces per-tool coverage gates (>95%).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the new tool project, wire it into the workspace, and ensure lint/test gates can run.

- [x] T001 Create new tool skeleton in mcp-tools/github-app-mcp/{pyproject.toml,README.md,src/github_app_mcp/,tests/}
- [x] T002 Add workspace member "mcp-tools/github-app-mcp" in pyproject.toml
- [x] T003 [P] Add tool package init + entrypoints in mcp-tools/github-app-mcp/src/github_app_mcp/{__init__.py,__main__.py}
- [x] T004 [P] Add baseline server skeleton in mcp-tools/github-app-mcp/src/github_app_mcp/server.py (stdio, list_tools/call_tool/list_resources/read_resource)
- [x] T005 [P] Add baseline errors + safety scaffolding in mcp-tools/github-app-mcp/src/github_app_mcp/{errors.py,safety.py}
- [x] T006 [P] Add baseline empty tool dispatch table in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py
- [x] T007 Configure tool-local pytest + coverage settings in mcp-tools/github-app-mcp/pyproject.toml (coverage >95%, omit server/entrypoint if consistent with repo)
- [x] T008 [P] Add smoke tests scaffold in mcp-tools/github-app-mcp/tests/test_scaffold.py (server imports, tools list non-empty, no secrets in basic outputs)
- [x] T009 [P] Add README scaffold including purpose, safety limits, and uvx snippet in mcp-tools/github-app-mcp/README.md

**Checkpoint**: `uv run pytest -q` runs in-container (may fail until implementation).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure required for ALL user stories: config, auth, GitHub API client, policy hooks, and audit logging.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T010 Implement config loading (env vars + defaults) in mcp-tools/github-app-mcp/src/github_app_mcp/config.py (GITHUB_APP_ID, GITHUB_APP_INSTALLATION_ID, GITHUB_APP_PRIVATE_KEY_PATH, policy env vars: GITHUB_APP_MCP_ALLOWED_REPOS, GITHUB_APP_MCP_PR_ONLY, GITHUB_APP_MCP_PROTECTED_BRANCHES, optional audit sink: GITHUB_APP_MCP_AUDIT_LOG_PATH)
- [x] T011 [P] Implement secret redaction helpers in mcp-tools/github-app-mcp/src/github_app_mcp/safety.py (redact tokens/private key content/path; enforce api.github.com host allowlist)
- [x] T012 [P] Implement structured audit logger in mcp-tools/github-app-mcp/src/github_app_mcp/audit.py (JSONL, correlation_id, allowed/denied/failed/succeeded, optional file sink)
- [x] T013 [P] Define error taxonomy and safe error serialization in mcp-tools/github-app-mcp/src/github_app_mcp/errors.py (no secret leakage)
- [x] T014 Implement GitHub App auth flow in mcp-tools/github-app-mcp/src/github_app_mcp/auth.py (JWT signing via private key path; installation token exchange; in-memory caching with expiry)
- [x] T015 Implement GitHub REST client wrapper in mcp-tools/github-app-mcp/src/github_app_mcp/github_client.py (httpx AsyncClient, explicit finite timeouts, bounded retries with backoff, rate-limit handling, safe logging)
- [x] T016 Implement policy evaluation core in mcp-tools/github-app-mcp/src/github_app_mcp/policy.py (repo allowlist, pr_only, protected branch rules, operation allowlist)
- [x] T017 Wire foundational modules into tool dispatch layer in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py (shared context construction per request; correlation ids)
- [x] T018 Add foundational unit tests for config + redaction + audit schema in mcp-tools/github-app-mcp/tests/test_foundation_{config,safety,audit}.py (include coverage for timeouts/bounded retries behavior and payload/file size limit enforcement where implemented)

**Checkpoint**: Server starts with `uv run python -m github_app_mcp --test` and lists tools/resources without throwing, and without leaking secrets.

---

## Phase 3: User Story 1 - GitHub actions via App identity (Priority: P1) 🎯 MVP

**Goal**: Allow-listed high-level GitHub operations execute strictly via GitHub App identity within installation scope, with no secret disclosure.

**Independent Test**: In a test repo where the app is installed, run: create branch → commit changes → open PR → comment; verify artifacts are attributed to the GitHub App and responses contain no secrets.

### Tests for User Story 1 (TDD)

- [x] T019 [P] [US1] Add contract tests for tool input validation in mcp-tools/github-app-mcp/tests/test_contract_schemas.py (reject extra fields, reject secrets; assert token-like inputs are rejected and error messages do NOT echo suspected secret values)
- [x] T020 [P] [US1] Add GitHub client request-mocking tests in mcp-tools/github-app-mcp/tests/test_github_client_requests.py (correct endpoints/headers; no token logged)
- [x] T021 [P] [US1] Add auth JWT + installation token caching tests in mcp-tools/github-app-mcp/tests/test_auth_token_cache.py
- [x] T053 [P] [US1] Add contract tests covering read tools in mcp-tools/github-app-mcp/tests/test_contract_schemas.py (including token-like input rejection + no-echo assertions)

### Implementation for User Story 1

- [x] T022 [P] [US1] Implement get_repository tool in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py (calls github_client; returns correlation_id + repo summary)
- [x] T023 [P] [US1] Implement create_branch tool in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py (read base ref → create ref)
- [x] T024 [US1] Implement commit_changes tool in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py using Git Data API via mcp-tools/github-app-mcp/src/github_app_mcp/github_client.py
- [x] T025 [P] [US1] Implement open_pull_request tool in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py
- [x] T026 [P] [US1] Implement comment_on_issue tool in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py
- [x] T027 [US1] Add per-tool audit events (allowed/succeeded/failed) in mcp-tools/github-app-mcp/src/github_app_mcp/{tools.py,audit.py}
- [x] T028 [US1] Add resource "server-status" and "capabilities" in mcp-tools/github-app-mcp/src/github_app_mcp/server.py and ensure it is non-secret
- [x] T029 [US1] Update contract docs to match implemented responses AND the allow-listed operation set (must match spec FR-005 allow-list) for all tools (including read tools: get_repository, list_branches, get_file, list_pull_requests, list_issues) and write tools (including optional next_steps guidance fields if added) in specs/002-github-app-mcp/contracts/mcp-contracts.json
- [x] T054 [P] [US1] Implement list_branches tool in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py (returns branch names + default branch; includes correlation_id)
- [x] T055 [P] [US1] Implement get_file tool in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py (reads a single file path at ref; size-limited; returns correlation_id)
- [x] T056 [P] [US1] Implement list_pull_requests tool in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py (basic PR list; returns correlation_id)
- [x] T057 [P] [US1] Implement list_issues tool in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py (basic issue list; returns correlation_id)

**Checkpoint**: US1 tools are usable end-to-end; responses include correlation_id; secrets never appear in responses.

---

## Phase 4: User Story 2 - Policy-enforced PR workflow (Priority: P2)

**Goal**: Server enforces PR-only workflows and protected-branch constraints, denying or guiding requests that attempt direct writes to protected branches.

**Independent Test**: With `GITHUB_APP_MCP_PR_ONLY=1` and a protected default branch, a request to commit to default branch is denied with safe guidance, and the agent can complete the flow via branch + PR.

### Tests for User Story 2 (TDD)

- [x] T034 [P] [US2] Add policy unit tests in mcp-tools/github-app-mcp/tests/test_policy.py (repo allowlist, pr_only, protected branches)
- [x] T035 [P] [US2] Add tool-level behavior tests for protected branch denials in mcp-tools/github-app-mcp/tests/test_tools_policy_enforcement.py

### Implementation for User Story 2

- [x] T036 [US2] Enforce repo allowlist + operation allowlist in mcp-tools/github-app-mcp/src/github_app_mcp/{policy.py,tools.py}
- [x] T037 [US2] Enforce protected-branch rule for write tools in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py (deny direct writes; return safe next_steps)
- [x] T038 [US2] Enforce PR-only workflow behavior in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py (deny direct-commit intent to protected branches; guide agent to create branch + open PR)
- [x] T039 [US2] Ensure policy decisions are fully audited (denied/allowed + reason) in mcp-tools/github-app-mcp/src/github_app_mcp/audit.py

**Checkpoint**: Mis-scoped or policy-violating requests are denied deterministically with safe guidance and audit entries.

---

## Phase 5: User Story 3 - Auditable, revocable automation (Priority: P3)

**Goal**: Every attempted operation is auditable and revocation/uninstall yields safe failures with audit traceability.

**Independent Test**: Run at least one successful read and one denied/failed write; verify audit JSONL entries include correlation_id, operation, repo, and outcome; simulate 401/403 from GitHub and confirm safe failure handling.

### Tests for User Story 3 (TDD)

- [x] T040 [P] [US3] Add audit log content tests in mcp-tools/github-app-mcp/tests/test_audit_events.py (no secrets, correlation id always present)
- [x] T041 [P] [US3] Add revocation/uninstall simulation tests in mcp-tools/github-app-mcp/tests/test_revocation_handling.py (GitHub 401/403 paths)

### Implementation for User Story 3

- [x] T042 [US3] Ensure all error paths emit audit entries with correlation_id in mcp-tools/github-app-mcp/src/github_app_mcp/{tools.py,audit.py,errors.py}
- [x] T043 [US3] Normalize GitHub auth failures into safe agent errors (no token/path leakage) in mcp-tools/github-app-mcp/src/github_app_mcp/errors.py
- [x] T044 [US3] Add minimal audit log retention controls (rotation/size cap or documented non-goal + safe defaults) in mcp-tools/github-app-mcp/src/github_app_mcp/config.py

**Checkpoint**: 100% of operations (including denied/failed) produce auditable records; revocation produces safe failures.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Tighten documentation, quality gates, and ensure the tool is ready for reviewers.

- [x] T045 [P] Add full README usage docs + environment variable reference in mcp-tools/github-app-mcp/README.md
- [x] T046 [P] Add uvx-from-GitHub config snippet (with #subdirectory) to mcp-tools/github-app-mcp/README.md
- [x] T047 [P] Add tool self-test mode documentation and example commands in mcp-tools/github-app-mcp/README.md
- [x] T048 Run `uv run pylint mcp-tools/*/src` and fix all pylint errors/warnings in mcp-tools/github-app-mcp/src/github_app_mcp/*.py
- [x] T049 Run `uv run ruff check --select D mcp-tools/github-app-mcp/src` and fix docstring issues in mcp-tools/github-app-mcp/src/github_app_mcp/*.py
- [x] T050 Run `uv run pytest -q` and ensure coverage >=95% for github-app-mcp (add tests in mcp-tools/github-app-mcp/tests/* as needed)
- [x] T051 Validate quickstart steps remain accurate in specs/002-github-app-mcp/quickstart.md (update if implementation uses different env var names; include explicit manual verification guidance for “artifacts attributable to GitHub App identity”)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2)
- **User Story 2 (P2)**: Can start after Foundational (Phase 2); integrates with US1 tools
- **User Story 3 (P3)**: Can start after Foundational (Phase 2); cross-cuts US1/US2 via audit + error handling

---

## Parallel Execution Examples

**US1 parallelization (different tools/files):**

- T022 (get_repository) can run in parallel with T023 (create_branch) and T025 (open_pull_request) and T026 (comment_on_issue) (all in mcp-tools/github-app-mcp/src/github_app_mcp/tools.py but should be implemented as separate functions to reduce merge conflicts).
- T019–T021 tests can be developed in parallel across separate test modules.

**US2 parallelization (policy + tests):**

- T034 (policy unit tests) can run in parallel with T035 (tool-level policy enforcement tests) in mcp-tools/github-app-mcp/tests/.

**US3 parallelization (audit + revocation):**

- T040 (audit event tests) can run in parallel with T041 (revocation handling tests) in mcp-tools/github-app-mcp/tests/.

**Setup parallelization:**

- T003–T006 can run in parallel (different files under mcp-tools/github-app-mcp/src/github_app_mcp/).

**Foundational parallelization:**

- T011–T013 can run in parallel (safety/audit/errors are independent files).

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE** using the independent test + quickstart scenario

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → validate independently
3. US2 → validate policy enforcement
4. US3 → validate auditability + revocation handling
5. Polish → final quality gates
