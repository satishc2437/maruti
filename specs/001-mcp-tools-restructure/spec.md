# Feature Specification: MCP Tools Restructure

**Feature Branch**: `001-mcp-tools-restructure`
**Created**: 2025-12-21
**Status**: Draft
**Input**: User description: "Repo-wide migration to align with the Constitution: move MCP tools under a repo-level mcp-tools/ folder, update devcontainer + root + tool docs/configs accordingly, add a root README, and flag (but do not delete) unwanted root files for removal."

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Use Tools From New Layout (Priority: P1)

As a contributor, I want every MCP tool to live under a single, consistent repo-level folder so I can find, run, and test each tool quickly without guessing paths.

**Why this priority**: This is the core migration goal. If tools aren’t reliably located and runnable from the new layout, the restructure provides no value.

**Independent Test**: A reviewer can verify the `mcp-tools/` layout exists and that each expected tool directory is present with documentation that references the new paths.

**Acceptance Scenarios**:

1. **Given** the repository is checked out, **When** I list the `mcp-tools/` directory, **Then** it contains tool folders for `agent-memory`, `onenote-reader`, `pdf-reader`, and `xlsx-reader`.
2. **Given** I open each tool’s README, **When** I follow its “Run” instructions, **Then** the instructions reference the `mcp-tools/<tool>/` path and do not reference the old repo-root tool paths.

---

### User Story 2 - Dev Environment Still Works (Priority: P2)

As a contributor using the repo’s standard container-based dev environment (“devcontainer”) and workspace defaults, I want them to work with the new tool layout so onboarding remains smooth after the restructure.

**Why this priority**: A restructure that breaks environment setup creates immediate churn and blocks new development.

**Independent Test**: A reviewer can validate that devcontainer documentation and scripts reference the `mcp-tools/` layout and provide a clear setup path.

**Acceptance Scenarios**:

1. **Given** I read devcontainer docs, **When** I follow setup instructions, **Then** the instructions reference the new tool paths under `mcp-tools/`.
2. **Given** I search the repo for old tool root paths, **When** I look for occurrences like `cd pdf-reader` or `cd xlsx-reader`, **Then** they do not appear in maintained documentation.

---

### User Story 3 - Root Cleanup Is Safe and Reviewable (Priority: P3)

As a maintainer, I want a clear list of repo-root files that look unnecessary after the restructure so we can review and remove them safely later, without accidental deletions.

**Why this priority**: Cleanup is valuable but must not risk data loss or disruptive changes.

**Independent Test**: A reviewer can confirm a “removal candidates” report exists and that no files were deleted as part of creating it.

**Acceptance Scenarios**:

1. **Given** the restructure is complete, **When** I open the removal-candidates report, **Then** it lists repo-root items that may be removable and states that nothing has been deleted.
2. **Given** the feature branch, **When** I inspect the changes, **Then** there are no deletions of repo-root items solely due to “cleanup”.

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

- Existing docs or scripts still reference old repo-root tool paths and need consistent updates.
- A tool directory is missing or renamed, causing partial migration (must be detected and corrected).
- Repo-root helper files may be legitimately needed (must be flagged for review, not deleted).
- Tool execution instructions differ per tool; docs must remain accurate per tool after the path move.

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: The repository MUST contain a top-level `mcp-tools/` directory.
- **FR-002**: The tools `agent-memory`, `onenote-reader`, `pdf-reader`, and `xlsx-reader` MUST exist as subdirectories under `mcp-tools/`.
- **FR-003**: Devcontainer configuration and documentation MUST reference the new `mcp-tools/` layout.
- **FR-004**: Tool documentation MUST reference the new `mcp-tools/<tool>/` paths (no maintained docs may instruct using the old repo-root tool paths).
- **FR-005**: The repository MUST include a repo-root `README.md` that explains the purpose of the repo and the `mcp-tools/` layout.
- **FR-006**: The feature MUST produce a repo-root report that flags potential removal candidates at repo root, and MUST explicitly state that no deletions are performed without confirmation.
- **FR-007**: The migration MUST NOT introduce cross-tool code dependencies (tools remain independently runnable and maintainable).

### Acceptance Criteria (Requirements)

- **AC-001 (FR-001)**: A top-level `mcp-tools/` directory exists in the repository.
- **AC-002 (FR-002)**: The four in-scope tools exist under `mcp-tools/` and are not present as top-level tool directories.
- **AC-003 (FR-003)**: Devcontainer docs and configurations reference `mcp-tools/` paths where tool paths are mentioned.
- **AC-004 (FR-004)**: Tool READMEs reference `mcp-tools/<tool>/` paths and do not instruct using the old repo-root tool paths.
- **AC-005 (FR-005)**: A repo-root `README.md` exists and describes the repo purpose and the `mcp-tools/` layout.
- **AC-006 (FR-006)**: A repo-root removal-candidates report exists and states that deletions require explicit confirmation.
- **AC-007 (FR-007)**: No new shared code is introduced that creates cross-tool runtime dependencies.



## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: 100% of the explicitly in-scope tools are located under `mcp-tools/` and no longer exist as top-level tool directories.
- **SC-002**: A contributor can identify the repo purpose and tool layout by reading only the repo-root README in under 2 minutes.
- **SC-003**: For each in-scope tool, a contributor can find and follow “Run” instructions that reference the `mcp-tools/<tool>/` path (no broken/contradictory path instructions).
- **SC-004**: A removal-candidates report exists and enables a maintainer to decide what to delete later (without any deletions performed as part of this feature).

## Assumptions

- The repo’s Constitution defines the standard development environment expectations; this feature updates structure and documentation to align with it.
- This feature is a restructure/migration; it does not change tool business functionality.

## Out of Scope

- Deleting or permanently removing repo-root files without explicit confirmation.
- Adding new MCP tools or new tool capabilities.
