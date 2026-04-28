# Dev Team

A multi-agent software development team for Claude Code. Drives a single work item — an Azure DevOps User Story/Bug or a GitHub issue — from intake through design, parallel implementation, code review, and PR creation.

## Roles

- **`team-lead`** (subagent) — orchestrator. Fetches the work item, designs the implementation, decomposes it into independent tasks, creates a feature branch and per-task worktrees, fans out to `software-developer` subagents in parallel, gates the result through `code-reviewer`, and opens the PR.
- **`software-developer`** (subagent) — implementer. Works inside a single git worktree on one task. Definition-of-done is **strict**: tests + linters must pass before reporting completion.
- **`code-reviewer`** (subagent) — read-only reviewer. Re-runs the test/lint gates and produces a structured **go/no-go** verdict with actionable feedback.
- **`/dev-team`** (slash command) — kickoff shortcut: `/dev-team <work-item-id>`. Platform (ADO vs GitHub) is auto-detected from `git remote get-url origin`.

## Install

From a Claude Code session in the target repo (no local checkout required):

```
/plugin marketplace add satishc2437/maruti
/plugin install dev-team@maruti
```

The first line is one-time per machine; subsequent installs from the same marketplace only need the second.

For local-checkout and project-local-copy options, see [`claude-code/README.md`](claude-code/README.md#install).

## Workflow

```
/dev-team 42
  └─► main agent
        └─► team-lead subagent
              ├── detect platform from `git remote get-url origin`
              ├── fetch work item (ADO MCP or `gh`)
              ├── analyze + design + decompose into N tasks
              ├── create feature branch + N worktrees
              ├── parallel fan-out:
              │     ├─► software-developer (task 1) ─┐
              │     ├─► software-developer (task 2) ─┤
              │     └─► software-developer (task N) ─┘
              ├── code-reviewer (go / no-go)
              │     └── on no-go: dispatch fixes back, repeat (max 3 iterations)
              └── on go: merge → push → open PR
```

## Operational policies

- **Loop:** auto-iterate developer ↔ reviewer up to **3 iterations**, then escalate to the human with a structured failure report.
- **Worktrees:** `.worktrees/<work-item-id>/<task-id>/` inside the repo, auto-added to `.gitignore`. **Auto-deleted on success**, kept on failure for forensics.
- **DoD (strict):** developers run the project's tests + linters; reviewer **re-runs** them. Red tests/linters = automatic no-go.
- **Branch template:** `users/satishc/feature/<work-item-id>-<slug>`
- **PR template:** title `[<work-item-id>] <work-item-title>`, body links back to the originating work item.

## External dependencies

| Integration | Tool |
|---|---|
| Azure DevOps (work items, repos, PRs) | `azure-devops-mcp` MCP server (the `team-lead` uses `mcp__azure-devops-mcp__*` tools) |
| GitHub (issues, repos, PRs) | `gh` CLI authenticated to the relevant org/repo |
| Worktree-per-task isolation | `git` ≥ 2.5 |

## Layout

```
packages/dev-team/
├── README.md                                    # this file
└── claude-code/
    ├── .claude-plugin/plugin.json
    ├── README.md                                # install / usage
    ├── agents/
    │   ├── team-lead.md
    │   ├── software-developer.md
    │   └── code-reviewer.md
    └── commands/
        └── dev-team.md
```

## Future extensions (not built)

- A cron-style watcher that polls an ADO query or GitHub search for unassigned/new work items in a queue and auto-launches `team-lead` for each. Would live alongside this package as an independent scheduler.
