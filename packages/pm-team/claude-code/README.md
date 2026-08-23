# PM Team — Claude Code variant

Installable Claude Code plugin bundling one skill (`pm-team`), three subagents (`requirements-analyst`, `spec-reviewer`, `board-manager`), and two slash commands (`/pm-team`, `/board-manager`).

## Install

### Option A — via the maruti marketplace (recommended)

Two-step flow from a Claude Code session in the target repo, no local checkout required:

```
/plugin marketplace add satishc-dev/maruti
/plugin install pm-team@maruti
```

The marketplace manifest lives at `.claude-plugin/marketplace.json` in the maruti repo root and registers all available plugins. The first command is one-time per machine; the marketplace stays registered across sessions.

To pin the marketplace to a specific tag or branch (rather than the default branch), add a ref suffix:

```
/plugin marketplace add satishc-dev/maruti@<tag-or-branch>
```

### Option B — from a local checkout

If you already have maruti cloned:

```
/plugin install <absolute-path>/packages/pm-team/claude-code
```

### Option C — project-local copy

```bash
mkdir -p .claude/agents .claude/commands .claude/skills/pm-team
cp packages/pm-team/claude-code/agents/*.md       .claude/agents/
cp packages/pm-team/claude-code/commands/*.md     .claude/commands/
cp packages/pm-team/claude-code/skills/pm-team/*  .claude/skills/pm-team/
```

## Prerequisites

| Integration | Setup |
|---|---|
| Azure DevOps | Install the `azure-devops-mcp` server and configure it with a PAT. The agents use `mcp__azure-devops-mcp__*` tools. |
| GitHub | `gh auth login` (or sandbox credential injection) for the org/repo where issues + PRs live. |

## Scrum cadence

The `pm-team` skill runs under a Scrum loop in ALL three modes (fresh, feedback, approved). The orchestrator:

1. **Phase 0:** reads `.scrum/lessons.md` (cross-project lessons memory, 5 KB FIFO) into planning context.
2. **Phase 1:** runs the mode-specific intake — interview + feature decomposition (fresh), PR-comment fetch + spec-branch checkout (feedback), merge verification + spec re-read (approved).
3. **Phase 2:** derives a project slug, writes a structured plan to `.scrum/<slug>/plan.md`, and **HALTS for explicit user signoff** before dispatching anyone. The plan covers project slug, mode, objective, team composition (`requirements-analyst-1`, `spec-reviewer-1`, `board-manager-1`, ...), task breakdown, cycle budget, project-level DoD, anticipated risks, and lessons applied.
4. **Phase 3:** initializes the journal (`.scrum/<slug>/agents/team-lead.md`).
5. **Phase 4:** runs the Scrum cycle loop (cycle = 1..budget). Each cycle: dispatch all `requirements-analyst-N` agents in parallel (via the `Task` tool with `run_in_background: true`, batched in one message), then dispatch `spec-reviewer-1` after they return (fresh / feedback); or dispatch `board-manager-1` alone (approved). Wait on each background task via `TaskOutput(task_id, block=true)` (or the automatic completion notification); use `TaskStop(task_id)` on any runaway. Prepend each subagent's schema-d work-log entry to `.scrum/<slug>/agents/<agentId>.md`. Warn the user at cycle `budget-2`, HALT at `budget` with continue/abort/finalize choice. Answer mid-loop status queries by reading the TOP entry of each agent's log.
6. **Phase 5:** writes `.scrum/<slug>/retrospective.md` and distills 1–3 project-agnostic lessons into `.scrum/lessons.md` (newest on top, 5 KB FIFO trim, whole-lesson eviction).
7. **Phase 6:** ships the terminal artifact per mode — open spec PR (fresh), push spec branch + reply to comments (feedback), capture WI URLs (approved).
8. **Phase 7:** final report with outcome, PR URL or WI URLs, cycle count consumed, retrospective path, and lessons added.

The default cycle budget is **12** (overridable with `--cycles N`, minimum 3); the previous 3-iteration `spec-reviewer` cap is REPLACED by this contract. The full on-disk layout, work-log schema, cycle budget contract, lessons FIFO rule, and retrospective format are documented in [`../SCRUM-SCHEMA.md`](../SCRUM-SCHEMA.md).

## Usage

### Start a new initiative

```
/pm-team I want a way to detect duplicate customer accounts
/pm-team I want a way to detect duplicate customer accounts --cycles 16
```

The skill will:

1. Conduct an interactive interview (≥3 rounds: scope, non-goals, constraints).
2. Decompose the intent into 2–5 features.
3. Read `.scrum/lessons.md`, derive a project slug, write `.scrum/<project-slug>/plan.md`, and **HALT for explicit user signoff** before dispatching anyone.
4. Spawn `requirements-analyst` subagents in parallel — one per feature — each producing `docs/specs/<initiative-slug>/<feature-slug>.md`. Persistent identities (`requirements-analyst-1`, `-2`, ...); each cycle they emit a schema-d work-log entry that the orchestrator prepends to `.scrum/<project-slug>/agents/<agentId>.md`.
5. Run `spec-reviewer-1` after each analyst pass; verdict lives in its work-log `Details` section. On `no-go`, re-dispatch only the affected analysts with the reviewer's `Required actions` verbatim. Cycle budget caps the loop.
6. On `go`: commit specs to branch `users/<you>/specs/<initiative-slug>` and open a **spec PR**.
7. Write `.scrum/<project-slug>/retrospective.md`, distill lessons into `.scrum/lessons.md`, report back.

### After PR review — comments to address

```
/pm-team feedback 1234
/pm-team feedback 1234 --cycles 8
```

Fetches PR #1234 comments, plans + asks for signoff, dispatches `requirements-analyst`s to revise the affected specs under the cycle budget, re-runs `spec-reviewer-1`, pushes to the same branch. Re-review.

### After PR review — approved

```
/pm-team approved 1234
/pm-team approved 1234 --cycles 6
```

Verifies PR #1234 is merged (asks you to merge if not), plans + asks for signoff (even for this single-`board-manager` flow), then dispatches `board-manager-1` to create the parent + child WIs on the board. Reports WI URLs; you hand off to `dev-team` per item:

```
/dev-team 5678
```

### Direct board operations (no PM flow)

```
/board-manager create a User Story for "audit log retention" with acceptance criteria X, Y, Z
/board-manager update WI 1234: set state to In Progress
/board-manager list all unassigned User Stories in the current sprint
```

Single-WI operations bypass the cycle budget. Multi-WI requests are routed back through `pm-team` so the Scrum cadence (plan + signoff, cycle budget, journal, retrospective) applies. The optional `--cycles N` flag applies to multi-WI operations only.

The platform (ADO vs GitHub) is auto-detected from `git remote get-url origin` — pass `--platform <ado|gh>` only if the repo has ambiguous remotes.
