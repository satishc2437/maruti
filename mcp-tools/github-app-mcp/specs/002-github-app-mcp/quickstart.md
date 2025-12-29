# Quickstart: github-app-mcp

**Feature**: `002-github-app-mcp`
**Date**: 2025-12-22

This quickstart is a reviewer-oriented guide for implementing and validating `github-app-mcp` inside the devcontainer.

## Goal

Enable AI agents to perform a limited set of GitHub repository operations strictly via a GitHub App identity, with policy enforcement and audit logging, and without exposing any secrets to the agent.

## Prerequisites

- A GitHub App created in the target GitHub org/user.
- The app installed on one or more repositories.
- The app granted the minimal required permissions (read/write as needed).
- The app private key downloaded as a `.pem` file stored on the host.

## Host-provided configuration (secrets stay local)

The server must be configured using host environment variables (which can be supplied via MCP client configuration inputs such as `mcp.json`).

Required inputs:

- `GITHUB_APP_ID`
- `GITHUB_APP_INSTALLATION_ID`
- `GITHUB_APP_PRIVATE_KEY_PATH` (path to the `.pem` file)

Optional policy inputs:

- `GITHUB_APP_MCP_ALLOWED_REPOS` (comma-separated `owner/repo`)
- `GITHUB_APP_MCP_PR_ONLY` (`1`/`0`)
- `GITHUB_APP_MCP_PROTECTED_BRANCHES` (comma-separated branch names/patterns)
- `GITHUB_APP_MCP_AUDIT_LOG_PATH` (optional file sink for JSONL audit events)

## Intended validation steps (in-container)

Once the tool is implemented under `mcp-tools/github-app-mcp/`:

1. Run tests:
   - `cd mcp-tools/github-app-mcp && uv run pytest -q`
2. Run pylint gate:
   - `uv run pylint mcp-tools/*/src`
3. Smoke test the server entrypoint (local):
   - `uv run python -m github_app_mcp --test`

## Manual scenario test

Using an MCP client configured with the above environment variables:

1. Call `create_branch` on an allow-listed repo.
2. Call `commit_changes` with a small set of file updates.
3. Call `open_pull_request` targeting the default branch.
4. Call `comment_on_issue` on the created PR.

Expected outcomes:

- All actions are attributed to the GitHub App.
- No secret values appear in tool responses.
- Each response includes a correlation ID that can be found in the audit log.

Suggested verification (manual):

- Confirm the created PR shows the GitHub App identity as the actor (often shown as an app/bot identity) in the GitHub UI.
- Confirm any created comments show the GitHub App identity as the author in the GitHub UI.
- Confirm the audit log contains entries with matching `correlation_id` values from tool responses.
