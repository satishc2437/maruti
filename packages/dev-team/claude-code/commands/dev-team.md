---
description: Drive an Azure DevOps work item or GitHub issue through design, parallel implementation, code review, and PR creation via the dev-team subagents. Platform auto-detected from the git remote.
argument-hint: <work-item-id>
---

Invoke the `team-lead` subagent (via the `Task` tool) to drive a work item end-to-end.

User arguments: $ARGUMENTS

Parse `$ARGUMENTS` as the work-item ID — typically a numeric ID (e.g., `1234`, `42`). If the user passed `--platform <ado|gh>` explicitly, honor it; otherwise leave platform detection to `team-lead`.

If `$ARGUMENTS` is empty or unparseable as a work-item ID, ask the user to re-issue the command with an ID.

Then dispatch to the `team-lead` subagent with the prompt:

> Drive work item `<work-item-id>` from intake to a merge-ready PR. Auto-detect the platform from `git remote get-url origin` (`github.com` → `gh`, `dev.azure.com` / `visualstudio.com` → `ado`); if it's ambiguous, ask the user once. Then follow your standard workflow: fetch the work item, design and decompose, create the feature branch and per-task worktrees, fan out to `software-developer` subagents in parallel, gate the result through `code-reviewer` (auto-iterate up to 3 times on no-go), then open the PR. Report back with the PR URL on success or a structured failure summary on failure.

The team-lead handles everything from there. Do not attempt the workflow yourself in the main agent — delegate.
