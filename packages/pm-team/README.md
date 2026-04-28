# PM Team

A multi-agent product management team for Claude Code. Takes a one-line user intent through an interactive interview, decomposes it into features, produces parallel specs, gates them through a reviewer, opens a **spec PR** for human review, and on approval seeds the Azure DevOps or GitHub Kanban board with work items ready for [`dev-team`](../dev-team/) to pick up.

## Roles

- **`pm-team`** (skill) — orchestrator + intent interview. Loaded into the main agent's context (multi-turn interview is natural there). Routes between three modes: **fresh**, **feedback**, **approved**.
- **`requirements-analyst`** (subagent) — per-feature spec writer. Produces one `docs/specs/<initiative>/<feature>.md` per feature. Spawned in parallel.
- **`spec-reviewer`** (subagent) — read-only gate. Validates each spec for completeness, testability of acceptance criteria, scope alignment. Returns structured **go/no-go**.
- **`board-manager`** (subagent) — write-access to the tracker. Creates/updates/queries WIs on ADO or GitHub. Invokable both *from* the `pm-team` skill and **standalone** via `/board-manager`.
- **`/pm-team`** (slash command) — kickoff: three argument shapes for three modes.
- **`/board-manager`** (slash command) — direct board operations independent of the PM flow.

## Platform detection

Both slash commands deduce the platform from `git remote get-url origin`:

| Remote URL contains | Detected platform |
|---|---|
| `github.com` | GitHub (`gh` CLI) |
| `dev.azure.com` or `visualstudio.com` | Azure DevOps (`mcp__azure-devops-mcp__*`) |
| anything else / no remote | Ask the user once, then proceed |

Override with `--platform <ado\|gh>` if the repo has ambiguous remotes.

## Workflow (fresh mode)

```
/pm-team "I want a way to detect duplicate customer accounts"
  └─► main agent (with pm-team skill loaded)
        ├── interactive intent interview (≥3 rounds: scope, non-goals, constraints)
        ├── decompose into N features (target 2–5)
        ├── parallel fan-out:
        │     ├─► requirements-analyst (feature 1) → docs/specs/<init>/<feat-1>.md ─┐
        │     ├─► requirements-analyst (feature 2) → docs/specs/<init>/<feat-2>.md ─┤
        │     └─► requirements-analyst (feature N) → docs/specs/<init>/<feat-N>.md ─┘
        ├── spec-reviewer (go / no-go, ≤3 iterations)
        └── on go:
              ├── commit specs to branch users/satishc/specs/<initiative-slug>
              ├── open spec PR
              └── STOP — wait for human review
```

## Workflow (feedback mode)

```
/pm-team feedback 1234
  └─► fetch PR comments via `gh pr view 1234 --json comments,reviews`
        ├── group comments by spec file
        ├── parallel fan-out:
        │     └─► requirements-analyst (revise spec X per comments) ─...─┐
        ├── spec-reviewer re-gate (≤3 iterations)
        ├── push to same branch
        └── (optional) reply to each addressed comment with "Resolved in <sha>"
```

You re-review and either comment again (loop) or approve.

## Workflow (approved mode)

```
/pm-team approved 1234
  └─► verify PR is merged (`gh pr view 1234 --json mergedAt`)
        ├── if not merged: ask you to merge first
        └── if merged:
              ├─► board-manager: create parent (Feature / labeled Issue) + N child User Stories
              ├── set fields, apply labels, link parent-child
              └── report PR + WI URLs; suggest `/dev-team <wi-id>` for each
```

## Operational policies

- **Spec doc location:** `docs/specs/<initiative-slug>/<feature-slug>.md` (grouped by initiative).
- **WI hierarchy:** two-level. Parent = Feature (ADO) or `feature`-labeled Issue (GitHub). Children = User Stories.
- **WI titles:** parent `[<initiative>] <feature title>`; child `<feature title>: <user story title>`.
- **GitHub parent-child:** sub-issues if the repo's issue types support them; `feature` label + `Parent: #<n>` body line as fallback.
- **Spec output:** both — repo is canonical (versioned, PR-able); WI body is a digest with a link to the spec file on `main`.
- **`spec-reviewer` cap:** 3 iterations per fan-out cycle; outer human-in-the-loop on the PR is unbounded.
- **No auto-merge:** PM team never merges the spec PR. You merge when ready; PM team verifies the merge before creating WIs.
- **`/board-manager` ops:** create, update, query (no bulk in v1).
- **Handoff:** PM exits after WIs are on the board. Invoke `/dev-team <wi-id>` per item.

## External dependencies

| Integration | Tool |
|---|---|
| Azure DevOps (work items, repos, PRs) | `azure-devops-mcp` MCP server (the agents use `mcp__azure-devops-mcp__*` tools) |
| GitHub (issues, repos, PRs) | `gh` CLI authenticated to the relevant org/repo |

## Layout

```
packages/pm-team/
├── README.md                                    # this file
└── claude-code/
    ├── .claude-plugin/plugin.json
    ├── README.md                                # install / usage
    ├── skills/
    │   └── pm-team/
    │       └── SKILL.md
    ├── agents/
    │   ├── requirements-analyst.md
    │   ├── spec-reviewer.md
    │   └── board-manager.md
    └── commands/
        ├── pm-team.md
        └── board-manager.md
```

## Future extensions (not built)

- Same feedback-loop pattern for `dev-team`'s code PR (fetch comments → revise → re-review → push).
- A cron-style watcher for unassigned/new initiatives in a queue.
- Bulk WI operations on `/board-manager`.
