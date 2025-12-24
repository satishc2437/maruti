# Data Model: GitHub Project Task Queue

**Date**: 2025-12-23
**Feature**: [specs/003-github-project-tasks/spec.md](spec.md)

## Entities

### Project
Represents the single shared GitHub Project (Projects v2) used as the task queue.

- **Identifiers**:
  - `owner_login` (string)
  - `project_number` (integer)
  - `project_id` (string; opaque node ID)
- **Attributes**:
  - `url` (string)
  - `title` (string)
- **Relationships**:
  - has many **ProjectField**
  - has many **ProjectItem**

### ProjectField
Represents a project field used to drive workflow (minimum required: a status-like single-select field).

- **Identifiers**:
  - `field_id` (string; opaque)
- **Attributes**:
  - `name` (string)
  - `data_type` (string; e.g., single-select)
  - `options` (array; for single-select fields only)

### ProjectFieldOption
Represents a single allowed value in a single-select project field.

- **Identifiers**:
  - `option_id` (string; opaque)
- **Attributes**:
  - `name` (string)

### Issue
Represents a GitHub Issue that is the durable task object.

- **Identifiers**:
  - `owner` (string)
  - `repo` (string)
  - `number` (integer)
  - `issue_node_id` (string; opaque)
- **Attributes**:
  - `title` (string)
  - `body` (string)
  - `state` (open/closed)
  - `url` (string)
  - optional metadata:
    - `labels` (array of strings)
    - `assignees` (array of strings)
    - `milestone` (string or integer, depending on contract choice)

### ProjectItem
Represents the project row/card that references an Issue.

- **Identifiers**:
  - `item_id` (string; opaque)
- **Attributes**:
  - `content_type` (expected: `issue`)
  - `status` (single-select option id + display name)
- **Relationships**:
  - references exactly one **Issue** (for this feature’s scope)

## Validation / Rules

- A `Project` must be allowlisted (host configuration).
- A repo must be allowlisted for repository-scoped tools.
- A `ProjectItem` status update must use a valid `field_id` and a valid option id from that field.
- Listing operations must be paginated and bounded.
