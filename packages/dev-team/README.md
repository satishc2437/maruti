# Dev Team

A multi-agent software development team for Claude Code. Drives a single work item — an Azure DevOps User Story/Bug or a GitHub issue — from intake through design, parallel implementation, code review, and PR creation.

## Roles

- **`dev-team`** (skill) — orchestrator. Loaded into the main agent's context (where the `Task` tool is available) by the `/dev-team` slash command. Reads cross-project lessons, fetches the work item, writes a structured plan and gets explicit user signoff before dispatching anyone, OPTIONALLY runs a Dev Design review (Phase 2.5, gated by `--design <auto|required|skip>`) with its own signoff gate, runs a Scrum cycle loop dispatching `software-developer` and `code-reviewer` subagents (via `Task` + `run_in_background: true` for parallel fan-out), writes a retrospective at the end, and opens the PR.
- **`software-developer`** (subagent) — implementer. Works inside a single git worktree on one task. Definition-of-done is **strict**: tests + linters must pass before reporting completion. Bounded by a per-turn budget; emits a schema-d work-log entry every cycle.
- **`code-reviewer`** (subagent) — read-only reviewer. Re-runs the test/lint gates and produces a structured **go/no-go** verdict with actionable feedback, emitted inside a schema-d work-log entry.
- **`/dev-team`** (slash command) — kickoff shortcut: `/dev-team <work-item-id> [--cycles <N>] [--design <auto|required|skip>]`. Platform (ADO vs GitHub) is auto-detected from `git remote get-url origin`. `--design` defaults to `auto` (the orchestrator recommends design review based on complexity signals and asks you to confirm); use `required` to force a Dev Design signoff, or `skip` to bypass it for small changes.

## Install

**Claude Code** — from a Claude Code session in the target repo:

```
/plugin marketplace add satishc-dev/maruti
/plugin install dev-team@maruti
```

**GitHub Copilot CLI** — from a Copilot CLI session in the target repo:

```
copilot plugin marketplace add satishc-dev/maruti
copilot plugin install dev-team@maruti
```

For each platform, the marketplace-add line is one-time per machine; subsequent installs only need the install line. For local-checkout and project-local-copy alternatives, see [`claude-code/README.md`](claude-code/README.md#install) and [`github-copilot/README.md`](github-copilot/README.md).

> The Copilot variant uses the same Scrum cadence — orchestrator chat mode dispatches `software-developer` and `code-reviewer` via the `agent` tool one round-trip per cycle (no live polling). See `github-copilot/README.md` for the mechanics.

## Scrum cadence

Dev-Team runs under a Scrum loop. The orchestrator MUST:

1. **Read cross-project lessons** from `.scrum/lessons.md` (a FIFO 5 KB scratch-pad accumulated across past projects) and use them when planning.
2. **Write a plan and get user signoff** before dispatching any subagent. The plan covers project slug, objective, team composition (persistent agent identities like `software-developer-1`, `code-reviewer-1`), task breakdown, cycle budget, project-level DoD, anticipated risks, and lessons applied. It is written to `.scrum/<project-slug>/plan.md` and presented in chat; nothing dispatches until the user approves.
3. **Optionally run a Dev Design review (Phase 2.5)** controlled by `--design <auto|required|skip>` (default `auto`). In `auto`, the orchestrator weighs complexity signals (task count, new modules, schema changes, AC ambiguity, cross-cutting surface, security/concurrency) and asks you to confirm a `yes`/`no` recommendation. When run, the orchestrator authors `.scrum/<project-slug>/design.md` (architectural overview, components touched, interfaces, data model, alternatives, testing, risks, open questions), presents it in chat, and HALTS for explicit signoff before any worktree is created or subagent is dispatched.
4. **Run a cycle loop** with a hard cap (default 12, configurable via `--cycles N`, minimum 3). The orchestrator warns the user at cycle `cap-2` and HALTS at the cap, offering: continue (+N), abort, or finalize-with-current-state. Each subagent has a per-turn budget and emits a schema-d work-log entry as the final block of its response; the orchestrator (sole writer) prepends each entry to `.scrum/<project-slug>/agents/<agentId>.md`. Mid-loop status queries are answered by reading the top entry of each agent's log without dispatching new work.
5. **Write a retrospective + distill lessons** at project end. The retrospective lives at `.scrum/<project-slug>/retrospective.md`; if Phase 2.5 ran, the retrospective also assesses design accuracy. 1–3 project-agnostic lessons are prepended to `.scrum/lessons.md`, which is FIFO-trimmed to 5 KB (whole-lesson eviction; no mid-content splits).

The full on-disk layout, work-log schema, cycle budget contract, lessons FIFO rule, and retrospective format are documented in [`SCRUM-SCHEMA.md`](SCRUM-SCHEMA.md).

## Workflow

```
/dev-team 42 [--cycles 12] [--design auto|required|skip]
  └─► dev-team skill (loaded into main agent context — Task tool available)
        ├── Phase 0: read .scrum/lessons.md
        ├── Phase 1: detect platform + fetch work item
        ├── Phase 2: write .scrum/<slug>/plan.md and HALT for user signoff
        ├── Phase 2.5 (OPTIONAL, gated by --design): write .scrum/<slug>/design.md and HALT for user signoff
        ├── Phase 3: init journal + feature branch + per-task worktrees
        ├── Phase 4: Scrum cycle loop (cycle = 1..budget)
        │     ├── dispatch software-developer-N via Task + run_in_background=true (parallel)
        │     ├── await each via TaskOutput(block=true) or auto-notification
        │     ├── dispatch code-reviewer-1 after devs return
        │     ├── prepend each subagent's work-log entry to agents/<agentId>.md
        │     ├── observation entry into agents/team-lead.md
        │     ├── handle blockers / answer mid-loop status queries
        │     └── budget check (warn at cap-2; halt at cap)
        ├── Phase 5: write retrospective + distill lessons (FIFO 5 KB)
        ├── Phase 6: merge → push → open PR → teardown
        └── Phase 7: final report (PR URL, cycles used, retrospective path)
```

## Operational policies

- **Cycle budget:** default 12, configurable via `--cycles N` (N >= 3). Warn at `N-2`, halt at `N` with continue/abort/finalize choice. The previous 3-iteration cap is REPLACED by this contract.
- **Plan signoff:** mandatory and explicit. Even on small projects, the orchestrator presents the plan and waits for `yes` / `change` / `abort`.
- **Dev Design review:** OPTIONAL, controlled by `--design <auto|required|skip>` (default `auto`). In `auto`, the orchestrator recommends `yes` if two or more complexity signals fire (task count >= 3, new modules / interfaces, schema changes, AC ambiguity, cross-cutting surface, security/concurrency) and asks you to confirm. When run, design signoff is mandatory and explicit — same `yes` / `change` / `abort` semantics as plan signoff. `--design skip` reproduces the legacy fast-path.
- **Persistent agent identities:** the same `software-developer-1` is re-dispatched cycle after cycle and accumulates history in its own work-log file under `.scrum/<slug>/agents/`. The orchestrator is the SOLE writer to every file under `agents/`.
- **Lessons memory:** `.scrum/lessons.md` is cross-project, 5 KB FIFO, prepended on write, trimmed whole-lesson at boundary.
- **Worktrees:** `.worktrees/<work-item-id>/<task-id>/` inside the repo, auto-added to `.gitignore`. **Auto-deleted on success**, kept on failure for forensics.
- **DoD (strict):** developers run the project's tests + linters; reviewer **re-runs** them. Red tests/linters = automatic no-go.
- **Branch template:** `users/<you>/feature/<work-item-id>-<slug>`
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
├── SCRUM-SCHEMA.md                              # .scrum/ layout, schema, cycle budget, lessons FIFO
├── claude-code/                                 # installable Claude Code plugin
│   ├── .claude-plugin/plugin.json
│   ├── README.md                                # install / usage
│   ├── agents/
│   │   ├── team-lead.md
│   │   ├── software-developer.md
│   │   └── code-reviewer.md
│   └── commands/
│       └── dev-team.md
└── github-copilot/                              # installable Copilot CLI plugin
    ├── agents/
    │   └── dev-team.agent.md
    └── README.md
```

## Future extensions (not built)

- A cron-style watcher that polls an ADO query or GitHub search for unassigned/new work items in a queue and auto-launches `team-lead` for each. Would live alongside this package as an independent scheduler.
