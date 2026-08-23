# PM Team

A multi-agent product management team for Claude Code and GitHub Copilot. Takes a one-line user intent through an interactive interview, decomposes it into features, produces parallel specs, gates them through a reviewer, opens a **spec PR** for human review, and on approval seeds the Azure DevOps or GitHub Kanban board with work items ready for [`dev-team`](../dev-team/) to pick up. The orchestrator runs under a Scrum cadence — plan + user signoff before any subagent is dispatched, schema-d work-logs per persistent agent identity, a bounded cycle budget, and a retrospective + cross-project lessons memory at the end.

## Roles

- **`pm-team`** (skill) — orchestrator + intent interview. Loaded into the main agent's context (multi-turn interview is natural there). Routes between three modes: **fresh**, **feedback**, **approved**. Reads cross-project lessons, writes a structured plan, halts for user signoff, runs the Scrum cycle loop, writes a retrospective at completion.
- **`requirements-analyst`** (subagent) — per-feature spec writer. Produces one `docs/specs/<initiative>/<feature>.md` per feature. Persistent identity (`requirements-analyst-1`, `-2`, ...); re-dispatched cycle-after-cycle. Emits a schema-d work-log entry as the FINAL block of its response.
- **`spec-reviewer`** (subagent) — read-only gate. Validates each spec for completeness, testability of acceptance criteria, scope alignment. Emits a structured **go/no-go** verdict INSIDE its work-log entry's `Details` section.
- **`board-manager`** (subagent) — write-access to the tracker. Creates/updates/queries WIs on ADO or GitHub. Invokable *from* the `pm-team` skill under Scrum, or **standalone** via `/board-manager` for single-WI operations.
- **`/pm-team`** (slash command) — kickoff: three argument shapes for three modes, plus optional `--cycles <N>`.
- **`/board-manager`** (slash command) — direct single-WI board operations independent of the PM flow. Multi-WI requests route back through `pm-team`.

## Install

**Claude Code** — from a Claude Code session in the target repo:

```
/plugin marketplace add satishc-dev/maruti
/plugin install pm-team@maruti
```

**GitHub Copilot CLI** — from a Copilot CLI session in the target repo:

```
copilot plugin marketplace add satishc-dev/maruti
copilot plugin install pm-team@maruti
```

For each platform, the marketplace-add line is one-time per machine; subsequent installs only need the install line. For local-checkout and project-local-copy alternatives, see [`claude-code/README.md`](claude-code/README.md#install) and [`github-copilot/README.md`](github-copilot/README.md).

> The Copilot variant runs the same Scrum cadence as Claude Code — orchestrator chat mode dispatches `requirements-analyst`, `spec-reviewer`, and `board-manager` via the `agent` tool one round-trip per cycle (no live polling). See `github-copilot/README.md` for the mechanics.

## Scrum cadence

PM-Team runs under a Scrum loop in ALL three modes (fresh, feedback, approved). Even a small project — for example, approved mode with a single `board-manager` dispatch — still goes through plan + user signoff, runs one cycle, writes a brief retrospective, and distills lessons. The orchestrator MUST:

1. **Read cross-project lessons** from `.scrum/lessons.md` (a FIFO 5 KB scratch-pad accumulated across past projects) and use them when planning.
2. **Write a plan and get user signoff** before dispatching any subagent. The plan covers project slug, mode, objective, team composition (persistent agent identities like `requirements-analyst-1`, `spec-reviewer-1`, `board-manager-1`), task breakdown, cycle budget, project-level DoD, anticipated risks, and lessons applied. It is written to `.scrum/<project-slug>/plan.md` and presented in chat; nothing dispatches until the user approves.
3. **Run a cycle loop** with a hard cap (default 12, configurable via `--cycles N`, minimum 3). The orchestrator warns the user at cycle `cap-2` and HALTS at the cap, offering: continue (+N), abort, or finalize-with-current-state. Each subagent has a per-turn budget and emits a schema-d work-log entry as the final block of its response; the orchestrator (sole writer) prepends each entry to `.scrum/<project-slug>/agents/<agentId>.md`. Mid-loop status queries are answered by reading the top entry of each agent's log without dispatching new work.
4. **Write a retrospective + distill lessons** at project end. The retrospective lives at `.scrum/<project-slug>/retrospective.md`; 1–3 project-agnostic lessons are prepended to `.scrum/lessons.md`, which is FIFO-trimmed to 5 KB (whole-lesson eviction; no mid-content splits).

The full on-disk layout, work-log schema, cycle budget contract, lessons FIFO rule, and retrospective format are documented in [`SCRUM-SCHEMA.md`](SCRUM-SCHEMA.md).

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
/pm-team "I want a way to detect duplicate customer accounts" [--cycles 12]
  └─► main agent (with pm-team skill loaded)
        ├── Phase 0: read .scrum/lessons.md
        ├── Phase 1 (F1): interactive intent interview (≥3 rounds) + feature decomposition (2–5 features)
        ├── Phase 2: write .scrum/<slug>/plan.md and HALT for user signoff
        ├── Phase 3: init journal (.scrum/<slug>/agents/team-lead.md)
        ├── Phase 4: Scrum cycle loop (cycle = 1..budget)
        │     ├── dispatch requirements-analyst-N in parallel
        │     ├── dispatch spec-reviewer-1 after analysts return
        │     ├── prepend each subagent's schema-d work-log entry to agents/<agentId>.md
        │     ├── observation entry into agents/team-lead.md
        │     ├── handle blockers / answer mid-loop status queries
        │     └── budget check (warn at cap-2; halt at cap)
        ├── Phase 5: write retrospective + distill lessons (FIFO 5 KB)
        ├── Phase 6 (F5): commit specs to branch users/<you>/specs/<initiative-slug>, open spec PR
        └── Phase 7: final report (PR URL, cycles used, retrospective path)
```

## Workflow (feedback mode)

```
/pm-team feedback 1234 [--cycles 12]
  └─► fetch PR comments via `gh pr view 1234 --json comments,reviews`
        ├── Phase 0: read .scrum/lessons.md
        ├── Phase 1 (B1): group comments by spec file, check out spec branch
        ├── Phase 2: write .scrum/<slug>/plan.md and HALT for user signoff
        ├── Phase 3: init journal
        ├── Phase 4: Scrum cycle loop
        │     ├── dispatch requirements-analyst-N (one per spec file with comments) in parallel
        │     ├── dispatch spec-reviewer-1 after analysts return
        │     └── budget check
        ├── Phase 5: retrospective + lessons
        ├── Phase 6 (B5): commit, push to same branch, (optionally) reply to each addressed comment
        └── Phase 7: final report
```

You re-review and either comment again (loop) or approve.

## Workflow (approved mode)

```
/pm-team approved 1234 [--cycles 12]
  └─► verify PR is merged (`gh pr view 1234 --json mergedAt`)
        ├── Phase 0: read .scrum/lessons.md
        ├── Phase 1 (A1+A2): verify merge, re-read docs/specs/<initiative-slug>/*.md
        ├── Phase 2: write .scrum/<slug>/plan.md and HALT for user signoff
        ├── Phase 3: init journal
        ├── Phase 4: Scrum cycle loop (typically one cycle)
        │     └── dispatch board-manager-1 — creates parent (Feature / labeled Issue) + N child User Stories
        ├── Phase 5: retrospective + lessons
        ├── Phase 6 (A4): capture WI URLs
        └── Phase 7: final report — PR URL, WI URLs, suggest `/dev-team <wi-id>` per item
```

## Operational policies

- **Cycle budget:** default 12, configurable via `--cycles N` (N >= 3). Warn at `N-2`, halt at `N` with continue/abort/finalize choice. The previous 3-iteration `spec-reviewer` cap is REPLACED by this contract.
- **Plan signoff:** mandatory and explicit in ALL three modes. Even approved mode with a single `board-manager` dispatch presents the plan and waits for `yes` / `change` / `abort`.
- **Persistent agent identities:** the same `requirements-analyst-1` is re-dispatched cycle after cycle and accumulates history in its own work-log file under `.scrum/<slug>/agents/`. The orchestrator is the SOLE writer to every file under `agents/`.
- **Lessons memory:** `.scrum/lessons.md` is cross-project, 5 KB FIFO, prepended on write, trimmed whole-lesson at boundary.
- **Spec doc location:** `docs/specs/<initiative-slug>/<feature-slug>.md` (grouped by initiative).
- **WI hierarchy:** two-level. Parent = Feature (ADO) or `feature`-labeled Issue (GitHub). Children = User Stories.
- **WI titles:** parent `[<initiative>] <feature title>`; child `<feature title>: <user story title>`.
- **GitHub parent-child:** sub-issues if the repo's issue types support them; `feature` label + `Parent: #<n>` body line as fallback.
- **Spec output:** both — repo is canonical (versioned, PR-able); WI body is a digest with a link to the spec file on `main`.
- **No auto-merge:** PM team never merges the spec PR. You merge when ready; PM team verifies the merge before creating WIs.
- **`/board-manager` ops:** single-WI create, update, query. Multi-WI requests route back through `pm-team` so the Scrum cadence applies.
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
├── SCRUM-SCHEMA.md                              # .scrum/ layout, schema, cycle budget, lessons FIFO
├── claude-code/                                 # installable Claude Code plugin
│   ├── .claude-plugin/plugin.json
│   ├── README.md                                # install / usage
│   ├── skills/
│   │   └── pm-team/
│   │       └── SKILL.md
│   ├── agents/
│   │   ├── requirements-analyst.md
│   │   ├── spec-reviewer.md
│   │   └── board-manager.md
│   └── commands/
│       ├── pm-team.md
│       └── board-manager.md
└── github-copilot/                              # installable Copilot CLI plugin
    ├── agents/
    │   └── pm-team.agent.md
    └── README.md
```

## Future extensions (not built)

- A cron-style watcher for unassigned/new initiatives in a queue.
- Bulk WI operations on `/board-manager` (currently routed back through `pm-team`).
