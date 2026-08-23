# Dev Team — Claude Code variant

Installable Claude Code plugin bundling one skill (`dev-team`, the orchestrator), two subagents (`software-developer`, `code-reviewer`), and one slash command (`/dev-team`).

## Install

### Option A — via the maruti marketplace (recommended)

Two-step flow from a Claude Code session in the target repo, no local checkout required:

```
/plugin marketplace add satishc-dev/maruti
/plugin install dev-team@maruti
```

The marketplace manifest lives at `.claude-plugin/marketplace.json` in the maruti repo root and registers all available plugins. The first command is one-time per machine; the marketplace stays registered across sessions.

To pin the marketplace to a specific tag or branch (rather than the default branch), add a ref suffix:

```
/plugin marketplace add satishc-dev/maruti@<tag-or-branch>
```

### Option B — from a local checkout

If you already have maruti cloned:

```
/plugin install <absolute-path>/packages/dev-team/claude-code
```

### Option C — project-local copy

```bash
mkdir -p .claude/agents .claude/commands .claude/skills/dev-team
cp packages/dev-team/claude-code/agents/*.md             .claude/agents/
cp packages/dev-team/claude-code/commands/*.md           .claude/commands/
cp packages/dev-team/claude-code/skills/dev-team/SKILL.md .claude/skills/dev-team/
```

## Prerequisites

| Integration | Setup |
|---|---|
| Azure DevOps | Install the `azure-devops-mcp` server and configure it with a PAT. The `dev-team` skill will use `mcp__azure-devops-mcp__*` tools. |
| GitHub | `gh auth login` (or sandbox credential injection) for the org/repo you'll be raising PRs against. |
| Git worktrees | `git` ≥ 2.5 (any modern install). |

## Usage

Kick off a run via the slash command:

```
/dev-team 1234
/dev-team 1234 --cycles 16
/dev-team 1234 --design required
/dev-team 1234 --cycles 16 --design skip
```

The `dev-team` skill auto-detects whether `1234` is an Azure DevOps work item or a GitHub issue from `git remote get-url origin`. Override with `--platform <ado|gh>` if your repo has remotes pointing at both. `--cycles N` overrides the default Scrum cycle budget (default 12, minimum 3). `--design <auto|required|skip>` controls whether a Dev Design Doc is produced and gated on user signoff before implementation (default `auto`; the skill recommends yes/no based on complexity signals and asks you to confirm).

Or describe the work directly:

```
Drive work item 1234 through the dev-team
```

The `dev-team` skill will:

1. **Phase 0:** read `.scrum/lessons.md` (cross-project lessons memory, 5 KB FIFO) into planning context.
2. **Phase 1:** fetch the work item (title, description, acceptance criteria).
3. **Phase 2:** read the repo's `CLAUDE.md` / `README.md` and recent history, derive a project slug, write a structured plan to `.scrum/<slug>/plan.md`, and **HALT for explicit user signoff** before dispatching anyone.
4. **Phase 2.5 (OPTIONAL — gated by `--design`):** when design review is enabled (always for `--design required`; in `--design auto` if the orchestrator's complexity recommendation is confirmed by the user), write a Dev Design Doc to `.scrum/<slug>/design.md` covering architectural overview, components touched, interfaces & contracts, data model changes, alternatives considered, testing strategy, risks, and open questions; present it in chat and **HALT for explicit signoff** before any worktree is created or subagent is dispatched. `--design skip` bypasses this phase entirely.
5. **Phase 3:** initialize the journal (`.scrum/<slug>/agents/team-lead.md`), create the feature branch `users/<you>/feature/<work-item-id>-<slug>`, and one worktree per task under `.worktrees/<work-item-id>/`.
6. **Phase 4:** run the Scrum cycle loop (cycle = 1..budget). Each cycle: dispatch all `software-developer-N` agents in parallel (via the `Task` tool with `run_in_background: true`, batched in one message), then dispatch `code-reviewer-1` after they return. Wait on each background task via `TaskOutput(task_id, block=true)` (or the automatic completion notification); use `TaskStop(task_id)` on any runaway. Prepend each subagent's schema-d work-log entry to `.scrum/<slug>/agents/<agentId>.md`. Warn the user at cycle `budget-2`, HALT at `budget` with continue/abort/finalize choice. Answer mid-loop status queries by reading the TOP entry of each agent's log.
7. **Phase 5:** write `.scrum/<slug>/retrospective.md` (including a design-accuracy assessment if Phase 2.5 ran) and distill 1–3 project-agnostic lessons into `.scrum/lessons.md` (newest on top, 5 KB FIFO trim, whole-lesson eviction).
8. **Phase 6:** on `go`: merge worktrees → push branch → open PR via `az repos pr create` (ADO) or `gh pr create` (GitHub) → delete worktrees.
9. **Phase 7:** final report with outcome, PR URL, cycle count consumed, retrospective path, and lessons added.

The full on-disk layout, work-log schema, cycle budget contract, lessons FIFO rule, and retrospective format are documented in [`../SCRUM-SCHEMA.md`](../SCRUM-SCHEMA.md).
