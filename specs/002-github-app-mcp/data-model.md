# Data Model: github-app-mcp

**Feature**: `002-github-app-mcp`
**Date**: 2025-12-22

This document defines the conceptual entities and validation rules for `github-app-mcp`. These entities describe inputs/outputs and server-side state, without prescribing implementation details beyond what is necessary to make contracts testable.

## Entities

### 1) Operation Request
Represents a single agent-submitted intent to perform a GitHub operation.

**Fields**
- `operation`: string enum (allow-listed operations only)
- `repo`: object
  - `owner`: string
  - `name`: string
- `inputs`: object (operation-specific inputs)
- `request_id`: string (client-provided id or server-generated)
- `submitted_at`: timestamp

**Validation rules**
- `operation` MUST be one of the server’s allow-listed operations.
- `repo.owner` and `repo.name` MUST be non-empty and match safe identifier patterns.
- `inputs` MUST conform to the operation’s declared schema.
- Requests MUST NOT contain secrets (PATs, private keys, access tokens). If present, reject.

### 2) Policy
Represents server-side guardrails that constrain execution.

**Fields**
- `repo_allowlist`: optional set of `owner/name` strings
- `operations_allowlist`: set of allowed operations
- `pr_only`: boolean
- `protected_branches`: set of branch name patterns (exact names or simple glob-like patterns)
- `max_file_bytes`: integer
- `max_files_per_commit`: integer

**Validation rules**
- If `repo_allowlist` is configured, all operations MUST be limited to that allowlist.
- If `pr_only` is true, write intents MUST use a PR-based workflow (create branch → commit → open PR).
- If a target branch matches `protected_branches`, direct writes MUST be denied (or rerouted to PR flow).

### 3) Installation Scope
Represents the GitHub App installation scope enforced by GitHub.

**Fields**
- `app_id`: string/integer identifier (server-side)
- `installation_id`: string/integer identifier (server-side)
- `permissions`: map of permission → level (read/write)
- `repositories`: set of repos accessible via this installation

**Validation rules**
- Server MUST only operate within this scope.
- Agents MUST NOT be able to enumerate installation ids or tokens.

### 4) Audit Log Entry
A record of an attempted operation for enterprise-grade traceability.

**Fields**
- `correlation_id`: string (server-generated, returned to agent)
- `timestamp`: timestamp
- `operation`: string
- `repo`: `owner/name`
- `result`: enum (`allowed`, `denied`, `failed`, `succeeded`)
- `reason`: short string (non-secret)
- `metadata`: object (non-secret; e.g., branch names, PR number/url, commit sha)

**Validation rules**
- MUST be emitted for every attempted operation.
- MUST NOT include secrets (private key contents, tokens) or full file contents.

## State transitions (high level)

- `submitted` → (`denied` | `executing`)
- `executing` → (`succeeded` | `failed`)

## Notes

- “Installation Scope” is not chosen by the agent; it is configured by the host environment.
- Policy is expected to be host-configurable and evaluated before any GitHub API calls.
