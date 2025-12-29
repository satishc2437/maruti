# Feature Specification: github-app-mcp

**Feature Branch**: `002-github-app-mcp`
**Created**: 2025-12-22
**Status**: Draft
**Input**: User description: "Build a new MCP tool named github-app-mcp that lets AI agents interact with GitHub only via a GitHub App identity, enforcing strict scope/permissions, policy guardrails, and audit logging while keeping all secrets opaque to agents."

## User Scenarios & Testing *(mandatory)*

Per the repo constitution, delivered changes must also satisfy repo quality gates
(e.g., linting must pass with zero errors, pylint must have zero errors/warnings,
docstring checks must have zero warnings, tests must pass).

For this repo, the canonical pylint gate is: `uv run pylint mcp-tools/*/src` (uses repo `.pylintrc`).

### User Story 1 - GitHub actions via App identity (Priority: P1)

An AI agent can request high-level GitHub actions (read repository details, create a branch, commit file changes, open a pull request, comment on an issue) and the MCP server executes them using only the GitHub App identity, without ever requiring or exposing personal credentials.

**Why this priority**: This is the core value: safe, revocable, least-privilege automation that is attributable to a non-human identity.

**Independent Test**: Can be tested end-to-end against a test repository where the GitHub App is installed: the agent requests a branch + commit + PR; the server completes the actions and returns only the results (URLs/IDs), never secrets.

**Acceptance Scenarios**:

1. **Given** the server is configured with a GitHub App installation that has access to repo `R`, **When** the agent requests “read repository info for `R`”, **Then** the server returns repository metadata allowed by permissions and does not return any tokens, keys, or installation identifiers.
2. **Given** the agent provides a set of file changes for repo `R`, **When** the agent requests “commit these changes”, **Then** the server creates a commit attributed to the GitHub App on an allowed branch and returns the resulting commit reference.

---

### User Story 2 - Policy-enforced PR workflow (Priority: P2)

An AI agent can request changes that would normally be risky (e.g., direct updates to protected branches), and the server enforces guardrails such as “PR-only workflow” and “no direct changes to protected branches.”

**Why this priority**: Prevents accidental or unauthorized production-impacting changes while still enabling the agent to deliver work through reviewable pull requests.

**Independent Test**: Configure a repository with a protected default branch; the agent requests a change targeting that branch; the server refuses direct modification and instead provides safe guidance to complete the change via a new branch + pull request using allow-listed tools.

**Acceptance Scenarios**:

1. **Given** repo `R` has a protected default branch, **When** the agent requests “commit these changes to the default branch”, **Then** the server blocks the direct write and returns safe next_steps guidance to complete the change via a new branch + pull request using allow-listed tools.

---

### User Story 3 - Auditable, revocable automation (Priority: P3)

Security and platform teams can understand “who did what, where, and when” for every action, and can immediately revoke access by changing the GitHub App installation/permissions without needing to rotate personal credentials.

**Why this priority**: Enterprise-grade auditability and revocability are key for operational trust.

**Independent Test**: Execute a read and a write operation; verify that both produce audit entries that include operation type, target repo, outcome, and correlation ID; uninstall the app and confirm subsequent operations fail safely.

**Acceptance Scenarios**:

1. **Given** the GitHub App is uninstalled (or permissions are reduced) for repo `R`, **When** the agent requests any operation on `R`, **Then** the server denies the request with a clear error and records the denial in the audit log.

---

### Edge Cases

- The agent requests an action for a repository where the app is not installed.
- The agent requests an action outside granted GitHub App permissions (e.g., trying to write without contents permission).
- Branch name conflicts (branch already exists) during “create branch” requests.
- Branch protection rules prevent direct updates to the target branch.
- API rate limiting or transient failures occur mid-operation (server must fail safely and record the outcome).
- The agent attempts to access or exfiltrate secrets (private key, tokens, installation identifiers).
- The agent attempts a raw/unspecified API call outside the supported operations.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST authenticate to GitHub exclusively as a GitHub App (not a user) and MUST perform all GitHub operations under that GitHub App identity.
- **FR-002**: The system MUST NOT accept, request, store, or use personal credentials or personal access tokens (PATs) for GitHub operations. The system MUST reject any agent-provided inputs that appear to be credentials, including:
  - Token-like prefixes/patterns (at minimum): `ghp_`, `gho_`, `ghu_`, `ghs_`, `github_pat_`, `Bearer `.
  - Credential-like field names in structured inputs (at minimum): `token`, `access_token`, `authorization`, `password`, `private_key`, `pem`, `jwt`.
  - Any value that matches the tool’s own installation token/JWT formats.
  Matching rules (minimum, for deterministic behavior):
  - Matching MUST be case-insensitive for field names; field-name matching MUST be exact after trimming whitespace.
  - Token-like prefix matching MUST be applied to any string input value after trimming leading whitespace and MUST check prefix-at-start (not substring).
  - On rejection, the system MUST NOT echo the suspected secret value in agent-visible errors, logs, or audit `reason` fields (only generic, non-secret guidance).
  - False positives MUST be handled as safe denials (with correlation_id and non-secret guidance), never as partial execution.
- **FR-003**: The system MUST obtain short-lived installation access tokens as needed and MUST treat them as secrets (never returning them to agents and never logging them in plaintext).
- Token lifecycle (minimum):
  - App JWTs MUST be short-lived (max 10 minutes).
  - Installation access tokens MAY be cached in-memory and MUST be refreshed before expiry (recommended: refresh when remaining lifetime < 30 seconds).
  - Tokens MUST NOT be persisted to disk.
- **FR-003a**: The system MUST load the GitHub App private key from a local file path provided via a local environment variable supplied by the host environment (e.g., via MCP client configuration inputs such as `mcp.json`) and MUST NOT accept the private key material directly from agent requests.
- Startup/config validation (minimum):
  - If required configuration is missing or invalid (missing env vars, non-integer IDs, unreadable/invalid key file), the server MUST fail fast at startup with a clear, non-secret message.
  - Errors MUST NOT include the private key contents, installation token/JWT, installation IDs, or the private key path.
- **FR-004**: The system MUST restrict all operations to repositories where the GitHub App is installed and to the permissions granted to that installation.
- **FR-005**: The system MUST expose only a controlled, allow-listed set of high-level operations (no generic “call arbitrary GitHub API” capability).

Allow-listed operations (minimum):

- `get_repository`
- `list_branches`
- `get_file`
- `list_pull_requests`
- `list_issues`
- `create_branch`
- `commit_changes`
- `open_pull_request`
- `comment_on_issue`

Prohibited operations / explicit non-goals (minimum):

- Any generic GitHub API passthrough (raw REST path/method passthrough, arbitrary headers, arbitrary GraphQL queries).
- Any operation that attempts to modify branch protection rules, repository settings, or GitHub App installation configuration.
- Any operation that attempts to expose or return secrets (private key material/path, JWTs, installation access tokens, installation IDs, numeric GitHub App ID).
- Force-push, history rewrite, or direct writes to protected branches when policy forbids it.
- **FR-006**: The system MUST support read operations within scope (at minimum: repository metadata, branches, files, pull requests, and issues) subject to granted permissions.
- **FR-007**: The system MUST support write operations within scope (at minimum: create branch, commit file changes, open pull request, comment on issue/pull request) subject to granted permissions.
- **FR-008**: The system MUST enforce policy guardrails for write operations, including blocking direct writes to protected branches when configured and supporting a PR-only workflow.
- **FR-009**: The system MUST validate that agent requests are “high-level intent” and MUST reject requests that attempt to bypass policy (e.g., “force push”, “disable protection”, “expose tokens”).
- High-level intent boundaries (minimum):
  - Allowed: requests that map directly to allow-listed tools with fixed schemas (e.g., “create branch X from Y”, “open PR from head to base”, “comment on issue #N”).
  - Rejected: requests for low-level API control (e.g., “call POST /anything”, “send these headers”, “run this GraphQL query”, “disable protection”, “force push”).
- **FR-010**: The system MUST ensure that all created artifacts (commits, pull requests, comments) are attributable to the GitHub App identity.
- Objective evidence (minimum): reviewers can validate attribution by observing in the GitHub UI/API that the actor/author on created PRs and comments is the GitHub App identity (not a user).
- **FR-011**: The system MUST produce an audit log record for every attempted operation (allowed, denied, failed, and succeeded), including timestamp, operation type, target repo, outcome, and a correlation identifier.
- **FR-012**: The system MUST avoid storing long-lived secrets beyond what is required to identify and operate the GitHub App. Secrets and sensitive identifiers MUST remain opaque to agents, including: GitHub App private key material, any derived JWTs, installation access tokens, and the numeric GitHub App installation ID. The system MAY return standard GitHub artifact identifiers required to use results (e.g., repository full name, commit SHA, branch name, pull request number/URL, issue number/URL), provided it does not return the installation ID or any tokens/keys. The system MUST NOT return numeric GitHub App ID either.
- **FR-013**: The system MUST provide clear, non-secret error messages to agents when requests are denied or cannot be executed.

### Non-Functional Requirements

- **NFR-001**: The system MUST enforce finite network timeouts for all GitHub API calls and MUST NOT allow unbounded waits.
  - Default timeout budget (maximum): 60 seconds per tool call (including retries).
  - Per-request timeouts (maximum): connect 5 seconds; read 30 seconds.
- **NFR-002**: The system MUST enforce documented size limits for agent-supplied payloads and GitHub-returned file content to avoid unbounded memory usage.
  - `commit_changes` limits (maximum): 25 files per request; 50 KiB decoded content per file; 200 KiB decoded total content.
  - `get_file` limits (maximum): 100 KiB decoded content returned.
  - Binary file handling: unsupported by default; binary-like content MUST be rejected with a safe error.
- **NFR-003**: The system MUST use bounded retries (with backoff) for transient GitHub API failures and MUST fail safely with audited outcomes when retries are exhausted.
  - Retries (maximum): 3 attempts total (initial + up to 2 retries).
  - Retryable conditions (minimum): HTTP 429, HTTP 5xx, and network timeouts.
  - Non-retryable (minimum): HTTP 401/403/404 and schema/policy validation failures.
  - Backoff: exponential with jitter; maximum single backoff 5 seconds.
- **NFR-004**: The system MUST ensure logs, errors, and audit events are safe-by-default and MUST NOT include secret material or full file contents.
- **NFR-005**: The system MUST restrict network egress to GitHub API hosts and MUST NOT follow redirects to non-allowlisted hosts.
  - Host allowlist (minimum): `https://api.github.com`.

### Assumptions

- A server instance is configured for a specific GitHub App and one or more specific installations; agents cannot select or enumerate installations.
- Repositories the tool can operate on are limited to the app’s installation scope and may be further constrained by an explicit allowlist.
- Organization policies such as protected branches may already exist and must be respected.

### Dependencies & Constraints

- The feature depends on a GitHub App being created and installed on target repositories with appropriate permissions.
- The feature depends on the host environment providing access to the GitHub App private key file path via environment configuration; agents must not be able to read or infer the key.
- Network connectivity to GitHub must be available to execute operations.

### Configuration Inputs

The host environment MUST provide required configuration inputs; agents MUST NOT be able to read, infer, or override them.

Required (host-provided):
- `GITHUB_APP_ID`: The GitHub App ID used for App authentication.
- `GITHUB_APP_INSTALLATION_ID`: The installation ID that scopes operations to the configured installation.
- `GITHUB_APP_PRIVATE_KEY_PATH`: Local file path to the GitHub App private key `.pem` (path is treated as sensitive; never returned to agents).

Input formats (minimum):

- `GITHUB_APP_ID` and `GITHUB_APP_INSTALLATION_ID` MUST be decimal integers.
- `GITHUB_APP_PRIVATE_KEY_PATH` MUST be an absolute filesystem path.

Optional (host-provided policy controls):
- `GITHUB_APP_MCP_ALLOWED_REPOS`: Restricts operations to an explicit allowlist (e.g., `owner1/repo1,owner2/repo2`).
- `GITHUB_APP_MCP_PR_ONLY`: Enforces PR-only workflow when enabled.
- `GITHUB_APP_MCP_PROTECTED_BRANCHES`: Branch patterns treated as protected (when branch-protection detection is unavailable or undesired).
- `GITHUB_APP_MCP_AUDIT_LOG_PATH`: Optional file path sink for JSONL audit events (path treated as sensitive; never returned to agents).

Policy semantics (minimum):

- Installation binding: the server is bound to a single installation identified by `GITHUB_APP_INSTALLATION_ID`; agents MUST NOT be able to select or enumerate installations.
- Repo allowlist: if `GITHUB_APP_MCP_ALLOWED_REPOS` is set, operations MUST be denied for repos not in the allowlist.
- Protected branches:
  - A branch is treated as protected if it matches any configured pattern in `GITHUB_APP_MCP_PROTECTED_BRANCHES`.
  - If PR-only is enabled and protection status is unknown, the system MUST fail safe and treat the target branch as protected.
- PR-only workflow:
  - When `GITHUB_APP_MCP_PR_ONLY` is enabled, direct write operations targeting a protected branch MUST be denied.
  - The denial response SHOULD include safe next_steps guidance explaining how to complete the workflow via `create_branch` → `commit_changes` → `open_pull_request`.

Edge-case semantics (minimum):

- Branch name conflicts: `create_branch` MUST fail with a clear, non-secret error if the branch already exists (no auto-rename).
- Partial failures for multi-step operations: a tool call MUST be considered failed if any step fails; the system MUST emit exactly one audit event with `outcome=failed` and a non-secret `reason`. Rollback is not required.

### Acceptance Criteria

1. **Given** an agent request includes a PAT or personal credential, **When** the request is submitted, **Then** the system rejects it and records an audit entry (FR-002, FR-011).
2. **Given** an agent request includes a token-like prefix (e.g., `ghp_` or `Bearer `), **When** the request is submitted, **Then** the system rejects it without echoing the token back in the error, and records an audit entry (FR-002, FR-011, FR-013).
3. **Given** the host environment is configured with an environment variable pointing to a GitHub App private key file, **When** the server starts, **Then** it uses that key for GitHub App authentication without exposing the key contents or key path to agents (FR-003a).
4. **Given** an agent requests an operation on a repo where the app is not installed, **When** the request is submitted, **Then** the system denies it with a clear error and records an audit entry (FR-004, FR-011, FR-013).
5. **Given** an agent requests a supported write operation within an installed repo and granted permissions, **When** the system executes it, **Then** the resulting GitHub artifact is attributable to the GitHub App and the system records a corresponding audit entry (FR-007, FR-010, FR-011).
6. **Given** PR-only workflow is configured and the target branch is protected, **When** an agent requests a direct write to that branch, **Then** the system blocks the direct write, returns safe next_steps guidance to complete the change via branch + PR, and records an audit entry (FR-008, FR-011, FR-013).
7. **Given** an agent attempts a raw/unspecified operation outside the allow-listed set, **When** the request is submitted, **Then** the system rejects it and records an audit entry (FR-005, FR-009, FR-011).
8. **Given** any operation succeeds, fails, or is denied, **When** the operation completes, **Then** the audit log contains a correlation ID that is returned to the agent for traceability without exposing secrets (FR-011).
9. **Given** an agent requests an operation that is within the allow-listed set but the GitHub App lacks required permissions, **When** the request is submitted, **Then** the system fails safely with a clear error (no secrets) and records an audit entry (FR-004, FR-011, FR-013).
10. **Given** an agent requests `create_branch` for a branch name that already exists, **When** the request is submitted, **Then** the system fails safely with a clear error and records an audit entry (FR-013, FR-011).

### Key Entities *(include if feature involves data)*

### Audit Event Schema (minimum)

Every attempted operation MUST emit exactly one audit event with the following required fields:

- `timestamp` (RFC3339)
- `correlation_id` (string, unique per operation attempt)
- `operation` (string; one of the allow-listed tool names)
- `target_repo` (string; `owner/name`)
- `outcome` (string; one of: `allowed`, `denied`, `failed`, `succeeded`)
- `reason` (string; required when `outcome` is `denied` or `failed`, must be non-secret)
- `duration_ms` (integer; optional but recommended)

Audit events MUST NOT include: private key material, private key path, JWTs, installation access tokens, or installation IDs. Audit events MUST NOT include full file contents.

Correlation identifier requirements (minimum):

- `correlation_id` MUST be a random identifier for traceability and MUST NOT encode or include the installation ID.

- **Operation Request**: An agent-provided high-level intent (operation type + target repository + user-supplied inputs like branch name, commit message, file changes).
- **Policy**: Server-side rules that constrain execution (e.g., PR-only workflow, branch restrictions, repository allowlist).
- **Audit Log Entry**: A record of an attempted operation (who/what, when, where, outcome, correlation ID) without secret material.
- **Installation Scope**: The set of repositories and permissions granted to the GitHub App installation.

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: 100% of attempted operations (including denials and failures) generate an audit log entry that conforms to “Audit Event Schema (minimum)”, including correlation_id, operation, target_repo, timestamp, and outcome.
- **SC-002**: 0 operations require an agent to provide GitHub credentials; requests containing personal credentials/PATs are rejected.
- **SC-003**: In a protected-branch test repository, 100% of write attempts targeting a protected branch are blocked or converted into a PR-based workflow consistent with configured policy.
- **SC-004**: In a test installation, an agent can complete the primary flow (create branch → commit changes → open PR → add a comment) successfully on the first attempt.
