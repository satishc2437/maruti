# Dev-Team — GitHub Copilot variant

Installable form of Dev-Team for use in GitHub Copilot CLI as a custom agent.

## Install

From a Copilot CLI session in the target repository:

```
copilot plugin marketplace add satishc-dev/maruti
copilot plugin install dev-team@maruti
```

The first command is one-time per machine; subsequent installs only need the second line.

## Manual install

If you prefer to vendor the agent directly into a repo (no plugin system):

```bash
mkdir -p .github/agents
cp agents/dev-team.agent.md .github/agents/dev-team.agent.md
```

Copilot CLI also reads `~/.copilot/agents/` for personal-scope agents if you want it available across all your projects.

## Usage

Once installed, switch to the **Dev-Team** agent in your Copilot CLI session and give it a work item:

```
@dev-team Drive work item 1234
@dev-team Drive work item 1234 --cycles 16
@dev-team Drive work item 1234 --design required
@dev-team Drive work item 1234 --cycles 16 --design skip
```

Dev-Team will detect whether the tracker is Azure DevOps or GitHub from `git remote get-url origin`, then run the Scrum workflow:

1. **Phase 0:** read `.scrum/lessons.md` (cross-project lessons memory, 5 KB FIFO) into planning context.
2. **Phase 1:** fetch the work item via `azure-devops` MCP server or `gh issue view`.
3. **Phase 2:** derive a project slug, write a structured plan to `.scrum/<slug>/plan.md`, and **HALT for explicit user signoff** before dispatching anyone.
4. **Phase 2.5 (OPTIONAL — gated by `--design <auto|required|skip>`, default `auto`):** when design review is enabled (always for `required`; in `auto` if the orchestrator's complexity recommendation is confirmed by the user), write a Dev Design Doc to `.scrum/<slug>/design.md` covering architectural overview, components touched, interfaces & contracts, data model changes, alternatives considered, testing strategy, risks, and open questions; present it in chat and **HALT for explicit signoff** before any worktree is created or subagent is dispatched. `skip` bypasses this phase entirely.
5. **Phase 3:** initialize the journal (`.scrum/<slug>/agents/team-lead.md`), create the feature branch, and one worktree per task.
6. **Phase 4:** run the Scrum cycle loop. Each cycle Dev-Team dispatches `software-developer-N` agents in parallel via the `agent` tool, then dispatches `code-reviewer-1` after they return. Each `agent` dispatch is one round-trip — no live polling; if work isn't done, the subagent returns `status: in-progress` and Dev-Team re-dispatches next cycle. Default cycle budget is **12** (overridable with `--cycles N`, minimum 3). Warn at cycle `budget-2`, HALT at `budget` with continue/abort/finalize choice.
7. **Phase 5:** write `.scrum/<slug>/retrospective.md` (including a design-accuracy assessment if Phase 2.5 ran) and distill 1–3 project-agnostic lessons into `.scrum/lessons.md` (newest on top, 5 KB FIFO trim, whole-lesson eviction).
8. **Phase 6:** on `go`: merge worktrees → push branch → open PR via `az repos pr create` (ADO) or `gh pr create` (GitHub) → delete worktrees.
9. **Phase 7:** final report with outcome, PR URL, cycle count consumed, retrospective path, and lessons added.

The full on-disk layout, work-log schema, cycle budget contract, lessons FIFO rule, and retrospective format are documented in [`../SCRUM-SCHEMA.md`](../SCRUM-SCHEMA.md).

## Notes vs. the Claude Code variant

The Claude Code and Copilot variants share the same Scrum semantics (Phase 0 through 7), the same `.scrum/` schema, the same work-log entry format, the same cycle budget contract, and the same retrospective + lessons mechanics. The only mechanical differences:

- Claude Code dispatches subagents via the `Task` tool with `run_in_background: true` so a cycle's tasks run in parallel; waits on each via `TaskOutput(task_id, block=true)` or auto-notifications; terminates runaways via `TaskStop(task_id)`. Subagents are atomic from the orchestrator's view (no in-flight transcript peek — that would overflow context); cycle-level visibility is via the standup files in `.scrum/<slug>/agents/`.
- Copilot dispatches subagents via the `agent` tool. Multiple `agent` calls batched in a single message run concurrently per Copilot's standard parallel-tool-use semantics — so the same `software-developer-1` / `software-developer-2` parallel fan-out the Claude Code variant does is supported. What Copilot lacks is mid-flight visibility — there is no `TaskOutput`-equivalent for polling a running subagent and no `TaskStop`-equivalent for terminating a runaway agent. Each call is one round-trip that returns when the subagent has finished its turn; if a subagent doesn't finish within its `cycleTurnBudget`, it returns `status: in-progress` and Dev-Team re-dispatches it on the next cycle.
