# Quickstart: GitHub Project Task Queue

This quickstart describes the intended agent workflow once the feature is implemented.

## Prerequisites

- A GitHub App installed on the org/user that owns:
  - the target repositories (multiple)
  - the target GitHub Project (Projects v2)
- Host config provides required env vars:
  - `GITHUB_APP_ID`
  - `GITHUB_APP_INSTALLATION_ID`
  - `GITHUB_APP_PRIVATE_KEY_PATH`

## Additional configuration (new)

- `GITHUB_APP_MCP_ALLOWED_PROJECTS`: Comma-separated allowlist entries in the form `owner_login/project_number`.
  - Example: `octo-org/3`

## Minimal agent workflow

1) Resolve the project

- Call `get_project_v2_by_number` with `{ owner_login, project_number }`.

2) Discover status field and options

- Call `list_project_v2_fields` with `{ project_id }`.
- Agent selects the status field (by name, e.g. "Status") and records the `field_id` and option IDs (e.g., `Todo`, `In Progress`, `Done`).

3) Create tasks as Issues across multiple repos

For each task:
- Call `create_issue` with:
  - required: `{ owner, repo, title, body }`
  - optional: `{ labels, assignees, milestone }`

4) Add issues to the project queue

- Call `add_issue_to_project_v2` with `{ project_id, issue_node_id }`.

5) Fetch next tasks from the project

- Call `list_project_v2_items` with `{ project_id, status_option_id }` (where `status_option_id` is the single-select option id for the desired status, discovered via `list_project_v2_fields`).
- Agent chooses the next item and calls `get_project_v2_item` to load full details.

6) Mark in progress

- Call `set_project_v2_item_field_value` with `{ project_id, item_id, field_id, single_select_option_id }` for the "In Progress" option.

7) Work and report progress

- Call `comment_on_issue` to append progress notes.
- Call `update_issue` as needed to refine title/body/metadata.

8) Finish

- Optionally close the issue via `update_issue` (`state: closed`).
- Call `set_project_v2_item_field_value` to set status to "Done".

## Development commands (existing)

From `mcp-tools/github-app-mcp`:

- `uv sync --dev`
- `uv run python -m github_app_mcp --test`
- `uv run pytest -q`

## Baseline gate results (Phase 1)

- `cd mcp-tools/github-app-mcp && uv run pytest -q`: PASS
- `uv run pylint mcp-tools/*/src`: PASS

## Manual validation (SC-001)

To validate **SC-001** (25 Issues across at least 3 repositories) without relying on mocks:

1) Configure:
  - `GITHUB_APP_MCP_ALLOWED_REPOS` with at least 3 repos (e.g., `org/repo-a,org/repo-b,org/repo-c`)
  - `GITHUB_APP_MCP_ALLOWED_PROJECTS` with the chosen project (e.g., `octo-org/3`)

2) Resolve the project and discover the Status options:
  - `get_project_v2_by_number`
  - `list_project_v2_fields`

3) Create 25 Issues across the 3 repos (any distribution is fine) and add each to the project:
  - `create_issue` → capture `issue_node_id`
  - `add_issue_to_project_v2` using `{ project_id, issue_node_id }`

4) Confirm in the GitHub UI that the Project shows 25 new items, spanning at least 3 repos.
