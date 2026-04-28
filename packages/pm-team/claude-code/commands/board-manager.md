---
description: Run a board operation (create, update, or query) directly against the project's ADO or GitHub Kanban board, independent of the PM flow. Platform auto-detected from the git remote.
argument-hint: <natural-language request, e.g., "create a User Story for X with criteria Y, Z">
---

User request: $ARGUMENTS

Invoke the `board-manager` subagent (via the `Task` tool) with the user's request as its prompt. The subagent will:

1. Detect the platform from `git remote get-url origin` (or honor `--platform <ado|gh>` if present in `$ARGUMENTS`).
2. Parse the request into one of: **create**, **update**, **query**.
3. Execute via the appropriate tool (`gh` CLI, `az`, or `mcp__azure-devops-mcp__*`).
4. Return URLs and a one-line confirmation per affected WI.

If the request is ambiguous (missing WI type, missing title, ambiguous WI ID), `board-manager` will ask one focused clarifying question. Do not attempt the operation yourself in the main agent — delegate.
