---
description: Drive an Azure DevOps work item or GitHub issue through design, parallel implementation, code review, and PR creation via the dev-team subagents.
argument-hint: <ado|gh> <work-item-id>
---

Invoke the `team-lead` subagent (via the `Task` tool) to drive a work item end-to-end.

User arguments: $ARGUMENTS

Parse the arguments as `<platform> <work-item-id>`:

- `<platform>` is one of `ado` (Azure DevOps) or `gh` (GitHub).
- `<work-item-id>` is the numeric ID (e.g., `1234`, `42`).

If the arguments don't match this shape, ask the user to re-issue the command rather than guessing.

Then dispatch to the `team-lead` subagent with the prompt:

> Drive `<platform>` work item `<work-item-id>` from intake to a merge-ready PR. Follow your standard workflow: fetch the work item, design and decompose, create the feature branch and per-task worktrees, fan out to `software-developer` subagents in parallel, gate the result through `code-reviewer` (auto-iterate up to 3 times on no-go), then open the PR. Report back with the PR URL on success or a structured failure summary on failure.

The team-lead handles everything from there. Do not attempt the workflow yourself in the main agent — delegate.
