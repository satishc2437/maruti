# Research: GitHub Project Task Queue (Projects v2)

**Date**: 2025-12-23
**Feature**: [specs/003-github-project-tasks/spec.md](spec.md)

## Decision 1: Use GitHub GraphQL only for Projects v2

- **Decision**: Implement Projects v2 operations via GitHub’s GraphQL endpoint and keep the existing REST client for repository-scoped resources (Issues).
- **Rationale**: Projects v2 capabilities (project lookup by number, project fields, project items, updating item field values, adding issue to project) are GraphQL-first. Keeping REST for issues preserves existing patterns and avoids rewriting stable code paths.
- **Alternatives considered**:
  - **REST-only**: Not viable for Projects v2.
  - **Generic GraphQL passthrough tool**: Rejected; violates allow-list and “no arbitrary GitHub API calls” constraints.

## Decision 2: Add a dedicated, allow-listed GraphQL client (no arbitrary queries)

- **Decision**: Add a small GraphQL client wrapper that:
  - hardcodes the base host allowlist (`https://api.github.com`),
  - only calls `POST /graphql`,
  - sends fixed query/mutation documents per tool (no agent-supplied query strings),
  - returns safe, minimal parsed results.
- **Rationale**: Maintains the existing safety model (no arbitrary API access; strict auditing) while enabling required project features.
- **Alternatives considered**:
  - Reuse REST client with a `/graphql` path: possible, but separating concerns avoids accidental expansion of REST surface and simplifies error handling for GraphQL errors.

## Decision 3: Explicit Project allowlist

- **Decision**: Introduce a host-controlled allowlist for Projects.
- **Proposed format**: `GITHUB_APP_MCP_ALLOWED_PROJECTS` as a comma-separated list of `owner_login/project_number` entries (example: `octo-org/3,octo-org/7`).
- **Rationale**: Existing policy gates are repo-scoped. Projects are org/user scoped; without an explicit allowlist, project tools could enable broad discovery or modification.
- **Alternatives considered**:
  - Allowlist by Project node ID: stricter, but harder for operators to configure.
  - Infer allowlist from repo allowlist: insufficient because a single project spans many repos and may be org-wide.

## Decision 4: Minimal project operations (no project CRUD, no views, no field CRUD)

- **Decision**: Only implement the minimal operations needed for an agent-driven task queue:
  - Resolve project (`get_project_v2_by_number`)
  - Discover fields/options (`list_project_v2_fields`)
  - List items (`list_project_v2_items`)
  - Get one item (`get_project_v2_item`)
  - Add issue to project (`add_issue_to_project_v2`)
  - Update status (single-select field value) (`set_project_v2_item_field_value`)
- **Rationale**: Reduces attack surface and implementation burden while meeting the workflow.
- **Alternatives considered**:
  - Support project creation/field management: rejected as unnecessary for “agent works tasks from queue” scenario.

## Decision 5: “Full task object” maps to standard GitHub Issue fields (templates stay agent-side)

- **Decision**: Expand issue creation/update to include optional standard fields: `labels`, `assignees`, `milestone` (and `state` on update).
- **Rationale**: Provides flexibility for task templates and richer task metadata without introducing server-side templating logic.
- **Alternatives considered**:
  - Server-side templating: rejected as extra complexity and a new injection surface.

## Decision 6: Status handling uses single-select option IDs

- **Decision**: Treat “Status” as a single-select field and require updates to specify the option ID (discovered via `list_project_v2_fields`).
- **Rationale**: Avoids ambiguous matching by name and supports projects with custom option sets.
- **Alternatives considered**:
  - Set by option name: simpler UX but error-prone across similarly named options.
