# Feature Specification: GitHub Project Task Queue

**Feature Branch**: `003-github-project-tasks`
**Created**: 2025-12-23
**Status**: Draft
**Input**: User description: "Add a minimal set of GitHub App-backed MCP operations to let an agent create Issues across many repos, add them into a single GitHub Project (Projects v2), then fetch and process tasks from that Project one-by-one."

## Clarifications

### Session 2025-12-23

- Q: Should task creation support a fuller task object (templates/metadata), beyond just Issue title/body? → A: Expand `create_issue`/`update_issue` to support standard GitHub Issue fields (optional labels/assignees/milestone; state on update). Templates remain agent-side (e.g., fetched via `get_file` and rendered by the agent).

## User Scenarios & Testing *(mandatory)*

Per the repo constitution, delivered changes must also satisfy repo quality gates
(e.g., linting must pass with zero errors, pylint must have zero errors/warnings,
docstring checks must have zero warnings, tests must pass).

For this repo, the canonical pylint gate is: `uv run pylint mcp-tools/*/src` (uses repo `.pylintrc`).

### User Story 1 - Populate project from task list (Priority: P1)

An agent provides a list of tasks where each task targets a specific repository and includes Issue content (title/body) plus optional standard metadata (labels, assignees, milestone). The MCP creates one Issue per task in the specified repository and adds each Issue to a single shared GitHub Project so the Project becomes the canonical task queue.

**Why this priority**: This is the core value: turning an agent-generated plan into a durable, auditable backlog that spans many repositories.

**Independent Test**: Can be tested by creating Issues in two allowed repos and verifying both appear as items in the configured Project with the expected initial status.

**Acceptance Scenarios**:

1. **Given** a Project is allowed and two repositories are allowed, **When** the agent creates tasks for both repositories, **Then** the system creates the Issues and adds them to the Project.
2. **Given** a repository is not allowed, **When** the agent attempts to create a task in that repository, **Then** the operation is denied and returns an error with a `correlation_id`.

---

### User Story 2 - Work tasks one-by-one from the project (Priority: P2)

An agent reads tasks from the Project (filtered to an initial status such as "Todo"), selects one, moves it to "In Progress", performs work, records progress on the Issue, and marks it "Done" (and optionally closes the Issue).

**Why this priority**: This enables a reliable, repeatable agent execution loop driven by the Project queue.

**Independent Test**: Can be tested by creating a single Issue+Project item, fetching it via the Project list, transitioning status twice, and writing a progress update back to the Issue.

**Acceptance Scenarios**:

1. **Given** the Project contains at least one task item in the initial status, **When** the agent lists tasks and selects one, **Then** the system returns enough information to load the underlying Issue.
2. **Given** the agent is working on a task, **When** it updates the Issue and transitions the Project item status, **Then** subsequent reads reflect the updated Issue content and status.

---

### User Story 3 - Safe, allow-listed project access (Priority: P3)

An operator wants the server to remain strictly allow-listed and secret-safe while enabling project-task workflows. The system restricts access to a configured set of repositories and a configured set of Projects, and records audit events for every attempt.

**Why this priority**: Project access is organization/user scoped; without explicit restriction it would weaken the existing allowlist model.

**Independent Test**: Can be tested by attempting access to a disallowed Project and confirming the request is denied and audited.

**Acceptance Scenarios**:

1. **Given** a Project is not on the allowlist, **When** the agent calls any Project tool for it, **Then** the request is denied with an error and `correlation_id`.
2. **Given** an agent includes secret-like content in a request, **When** the tool is invoked, **Then** the request is rejected and no secrets are returned in errors.

---

### Edge Cases

- Project list results require pagination (agent must be able to continue listing without missing/duplicating items).
- The configured status field is missing from the Project (system returns a clear, actionable error).
- Requested status value does not exist in the Project’s configured options (system rejects the update).
- An Issue is already added to the Project (operation behaves deterministically and does not create duplicates).
- The Project contains non-Issue items (system returns them with a clear `content_type` so the agent can skip them deterministically).
- The GitHub App lacks permission for a specific repo or Project (system returns a safe error with a `correlation_id`).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The MCP server MUST expose allow-listed operations that support a Project-driven task queue spanning multiple repositories.
- **FR-002**: The MCP server MUST support targeting a single GitHub Project by an owner + project number and return stable identifiers for subsequent operations.
- **FR-003**: The MCP server MUST return the Project’s field definitions and allowed status options so an agent can safely set status values without hardcoding identifiers.
- **FR-004**: The MCP server MUST allow an agent to create an Issue in a specified allowed repository with `title` and `body`, plus optional standard Issue fields: `labels`, `assignees`, `milestone`.
- **FR-005**: The MCP server MUST allow an agent to add a created/existing Issue to the configured Project.
- **FR-006**: The MCP server MUST allow an agent to list Project items with pagination and an optional filter by status.
- **FR-007**: The MCP server MUST allow an agent to fetch a single Project item’s details, including enough information to identify and retrieve the underlying Issue.
- **FR-008**: The MCP server MUST allow an agent to update a Project item’s status to one of the Project’s configured status options.
- **FR-009**: The MCP server MUST allow an agent to retrieve an Issue by repository + issue number.
- **FR-010**: The MCP server MUST allow an agent to update an Issue’s `title`/`body`, optional standard fields (`labels`, `assignees`, `milestone`), and `state` (open/closed).
- **FR-011**: The MCP server MUST preserve the existing audit and safety guarantees for every new operation: every attempt emits an audit event and every response includes a `correlation_id`.
- **FR-012**: The MCP server MUST enforce existing repository allowlist rules for all repository-scoped operations.
- **FR-013**: The MCP server MUST enforce an explicit Project allowlist so the agent cannot read or modify arbitrary Projects.
- **FR-014**: The MCP server MUST reject requests containing secret-like material (tokens, private keys) consistent with existing secret-safety behavior.
- **FR-015**: The MCP server MUST return stable identifiers required for chaining operations, including `issue_node_id` from `create_issue` and `get_issue` so an agent can add the Issue to a Project via GraphQL.

### Allow-listed Operations (Minimum)

New operations required by this feature:

- `get_project_v2_by_number`: Identify the configured Project for task queue operations.
- `list_project_v2_fields`: Discover the Project’s status field and valid options.
- `list_project_v2_items`: Retrieve tasks from the Project (with optional status filtering by status option id).
- `get_project_v2_item`: Retrieve full task item details.
- `set_project_v2_item_field_value`: Update task status in the Project.
- `create_issue`: Create a task Issue in a specified repository.
- `get_issue`: Retrieve an Issue to load task details.
- `update_issue`: Update an Issue to record progress and optionally close it.
- `add_issue_to_project_v2`: Add an Issue to the Project queue.

Existing operation relied upon for progress logging:

- `comment_on_issue`: Append progress updates without overwriting Issue content.

### Assumptions

- A single GitHub Project is used as the canonical task queue.
- Tasks are represented as Issues (not draft items) and may belong to many repositories.
- If task templates are used, the agent fetches template content (for example, via `get_file`) and renders `title`/`body` client-side before calling `create_issue`.
- The Project has a single-select status field with a small set of options (for example: Todo / In Progress / Done). The agent discovers the exact options at runtime.
- The system enforces bounded pagination and request sizes:
	- `list_project_v2_items.page_size` default: 20; max: 50.
	- `list_project_v2_fields` returns the Project field definitions in a single response (no client-provided pagination parameter).
	- The server rejects `list_project_v2_items.page_size` above the max with a clear validation error.
- Status filtering semantics:
	- `list_project_v2_items` accepts an optional `status_option_id` (single-select option id from `list_project_v2_fields`).
	- If provided, filtering is performed server-side in the GraphQL query when feasible; otherwise the tool returns items including status so the agent can filter client-side without ambiguity.

### Tool Output Contract (Chaining)

- `create_issue` and `get_issue` return `issue_number`, `issue_node_id`, `owner`, `repo`.
- `get_project_v2_item` returns enough to load the underlying Issue, including `issue_number`, `issue_node_id`, `owner`, `repo`, plus `content_type`.

### Key Entities *(include if feature involves data)*

- **Project**: The shared task board; identified by owner login + project number; has fields and items.
- **Project Field**: A named field (e.g., status) with a known type and, for single-select, an allowed set of options.
- **Project Item**: A row/card in the Project that references an Issue; includes field values such as status.
- **Issue**: A repository-scoped work item created by the agent; identified by `owner/repo` + number and has title/body/state.
- **Task**: The agent’s conceptual unit of work represented by the Issue + its corresponding Project item.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An agent can create and add at least 25 Issues across at least 3 repositories into the configured Project without manual intervention.
- **SC-002**: An agent can fetch the next "Todo" task from the Project, mark it "In Progress", and later mark it "Done" with status values matching the Project’s configured options.
- **SC-003**: 100% of denied accesses to disallowed repositories or Projects return a safe error response and include a `correlation_id`.
- **SC-004**: No responses or audit logs include GitHub tokens, private keys, or installation identifiers.
