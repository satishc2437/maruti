# Research: github-app-mcp

**Feature**: `002-github-app-mcp`
**Date**: 2025-12-22

This research resolves key technical choices required to implement a GitHub-App-only MCP server that enforces policy guardrails and produces audit logs while keeping secrets opaque to agents.

## Decisions

### Decision: Use GitHub REST API via async HTTP client
- **Decision**: Use GitHub REST API (api.github.com) via `httpx.AsyncClient`.
- **Rationale**: Matches the repo’s async MCP server style, keeps dependencies modest, and avoids bringing in a large GitHub SDK that may hide rate-limit and error semantics.
- **Alternatives considered**:
  - PyGithub: rejected due to heavier dependency surface and less explicit control over request/response handling.
  - GitHub GraphQL: rejected for MVP because many required operations (refs/trees/blobs) are straightforward in REST and GraphQL adds schema/query complexity.

### Decision: GitHub App authentication with JWT + installation token exchange
- **Decision**: Implement GitHub App auth by signing a short-lived JWT using the app private key (RS256), then exchanging it for an installation access token.
- **Rationale**: This is GitHub’s intended GitHub App flow and ensures all actions are attributable to the app identity, not a user.
- **Alternatives considered**:
  - PAT / personal OAuth tokens: rejected (violates feature intent and FR-002).
  - GitHub CLI (`gh`) execution: rejected due to credential leakage risk and weaker control over token handling.

### Decision: Private key provisioning via host environment variable (path)
- **Decision**: Require the `.pem` private key to be provided as a local file path via a host-provided environment variable (e.g., `GITHUB_APP_PRIVATE_KEY_PATH`) configured by the MCP client (e.g., `mcp.json` inputs).
- **Rationale**: Keeps private key material and configuration out of agent-visible requests; supports separation of reasoning/execution and easy revocation/rotation.
- **Alternatives considered**:
  - Passing PEM contents in tool arguments: rejected (secrets would transit the agent channel).
  - Fetching the key from a remote secret manager: deferred (would add non-trivial operational dependencies).

### Decision: Commit implementation uses Git Data API for a single atomic commit
- **Decision**: Use the Git Data API (create blobs → create tree → create commit → update ref) to create one commit containing multiple file changes.
- **Rationale**: Supports the “commit these changes” intent as a single commit (better reviewability) and avoids per-file commits.
- **Alternatives considered**:
  - Contents API (`/contents/{path}`) per file: rejected for MVP because it produces one commit per file (or requires complex sequencing).

### Decision: Policy enforcement is primarily server-config driven
- **Decision**: Enforce “PR-only workflow” and protected-branch restrictions via server-side configuration and explicit deny-lists/allow-lists; optionally attempt branch-protection detection when permissions permit, but do not rely on it.
- **Rationale**: Branch protection APIs often require elevated permissions; policy enforcement must work even without them.
- **Alternatives considered**:
  - Rely exclusively on GitHub branch protection endpoints: rejected as fragile and permission-dependent.

### Decision: Audit logging as JSON lines with strict redaction
- **Decision**: Emit an audit event for every attempted operation (allowed/denied/failed) as JSON lines to stderr and optionally to a configured file sink.
- **Rationale**: JSONL is easy to ingest by enterprise logging systems; supports correlation IDs; avoids accidentally logging secrets.
- **Alternatives considered**:
  - Logging full request payloads: rejected due to secret/file-content leakage risk.
  - Storing audit data in a database: rejected for MVP to keep the tool self-contained.

### Decision: Retry/rate-limit behavior is explicit and safe
- **Decision**: Implement a small retry policy for transient 5xx errors and secondary rate limits; expose safe, non-secret error details to agents while logging full diagnostic context only in the server audit log (still redacted).
- **Rationale**: GitHub API can transiently fail; agents need actionable outcomes without gaining access to sensitive context.
- **Alternatives considered**:
  - Unlimited retries: rejected (risk of runaway actions and unbounded latency).

## Notes / Practical constraints

- Some desired “branch protection” enforcement may require admin-level permissions; the implementation will default to PR-only and config-driven branch restrictions to stay least-privilege.
- File-content handling must be bounded (size limits, allowed encodings). Large binary writes may be explicitly unsupported in MVP.
