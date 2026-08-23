# PM-Team — GitHub Copilot variant

Installable form of PM-Team for use in GitHub Copilot CLI as a custom agent. Runs the same Scrum cadence as the Claude Code variant.

## Install

From a Copilot CLI session in the target repository:

```
copilot plugin marketplace add satishc-dev/maruti
copilot plugin install pm-team@maruti
```

The first command is one-time per machine; subsequent installs only need the second line.

## Manual install

If you prefer to vendor the agent directly into a repo (no plugin system):

```bash
mkdir -p .github/agents
cp agents/pm-team.agent.md .github/agents/pm-team.agent.md
```

Copilot CLI also reads `~/.copilot/agents/` for personal-scope agents if you want it available across all your projects.

## Scrum cadence

PM-Team (Copilot) runs the same Scrum loop as the Claude Code variant in ALL three modes (fresh, feedback, approved). The orchestrator:

1. **Phase 0:** reads `.scrum/lessons.md` (cross-project lessons memory, 5 KB FIFO) into planning context.
2. **Phase 1:** runs the mode-specific intake — interview + feature decomposition (fresh), PR-comment fetch + spec-branch checkout (feedback), merge verification + spec re-read (approved).
3. **Phase 2:** derives a project slug, writes a structured plan to `.scrum/<slug>/plan.md`, and **HALTS for explicit user signoff** before dispatching anyone.
4. **Phase 3:** initializes the journal (`.scrum/<slug>/agents/team-lead.md`).
5. **Phase 4:** runs the Scrum cycle loop. Each cycle PM-Team dispatches `requirements-analyst-N` agents in parallel via the `agent` tool, then dispatches `spec-reviewer-1` after they return (fresh / feedback); or dispatches `board-manager-1` alone (approved). Each `agent` dispatch is one round-trip — no live polling; if work isn't done, the subagent returns `status: in-progress` and PM-Team re-dispatches next cycle. Default cycle budget is **12** (overridable with `--cycles N`, minimum 3). Warn at cycle `budget-2`, HALT at `budget` with continue/abort/finalize choice. Answer mid-loop status queries by reading the TOP entry of each agent's log.
6. **Phase 5:** writes `.scrum/<slug>/retrospective.md` and distills 1–3 project-agnostic lessons into `.scrum/lessons.md` (newest on top, 5 KB FIFO trim, whole-lesson eviction).
7. **Phase 6:** ships the terminal artifact per mode — open spec PR (fresh), push spec branch + reply to comments (feedback), capture WI URLs (approved).
8. **Phase 7:** final report with outcome, PR URL or WI URLs, cycle count consumed, retrospective path, and lessons added.

The full on-disk layout, work-log schema, cycle budget contract, lessons FIFO rule, and retrospective format are documented in [`../SCRUM-SCHEMA.md`](../SCRUM-SCHEMA.md).

## Usage

Once installed, switch to the **PM-Team** agent in your Copilot CLI session. PM-Team has three modes:

```
# Fresh: kick off a new initiative
@pm-team I want to plan a feature for detecting duplicate uploads
@pm-team I want to plan a feature for detecting duplicate uploads --cycles 16

# Feedback: address comments on an open spec PR
@pm-team address comments on PR 1234
@pm-team feedback 1234 --cycles 8

# Approved: seed the board after the spec PR is merged
@pm-team PR 1234 is approved, proceed
@pm-team approved 1234 --cycles 6
```

In `fresh` mode, PM-Team interviews you, decomposes the initiative into 2–5 features, writes a plan to `.scrum/<project-slug>/plan.md` and halts for your explicit signoff, then dispatches `requirements-analyst` subagents in parallel to draft `docs/specs/<initiative-slug>/<feature-slug>.md` files, gates them through `spec-reviewer-1`, opens a spec PR, writes a retrospective, and distills lessons — all under the cycle budget. After you merge, invoke `approved <pr#>` and PM-Team plans the board-seed (still requires your signoff), then dispatches `board-manager-1` to create parent Features and child User Stories ready for the `Dev-Team` agent to pick up.

The tracker platform (Azure DevOps vs GitHub) is auto-detected from `git remote get-url origin`.

## Notes vs. the Claude Code variant

The Claude Code and Copilot variants share the same Scrum semantics (Phase 0 through 7), the same `.scrum/` schema, the same work-log entry format, the same cycle budget contract, the same plan + user signoff requirement (universal across all three modes), and the same retrospective + lessons mechanics. The only mechanical differences:

- Claude Code's `pm-team` skill dispatches subagents via the `Task` tool with `run_in_background: true` so a cycle's tasks run in parallel; waits on each via `TaskOutput(task_id, block=true)` or auto-notifications; terminates runaways via `TaskStop(task_id)`. Subagents are atomic from the orchestrator's view (no in-flight transcript peek — that would overflow context); cycle-level visibility is via the standup files in `.scrum/<slug>/agents/`.
- The Copilot `PM-Team` chat mode dispatches subagents via the `agent` tool. Multiple `agent` calls batched in a single message run concurrently per Copilot's standard parallel-tool-use semantics — so the same `requirements-analyst-1` / `requirements-analyst-2` parallel fan-out the Claude Code skill does is supported. What Copilot lacks is mid-flight visibility — no `TaskOutput`-equivalent for polling a running subagent and no `TaskStop`-equivalent for terminating a runaway agent. Each call is one round-trip that returns when the subagent has finished its turn; if a subagent doesn't finish within its `cycleTurnBudget`, it returns `status: in-progress` and PM-Team re-dispatches it on the next cycle. Each dispatch carries the explicit instruction "You have a budgeted run. Do at most one turn of work, then return your work-log entry as the FINAL block of your response. Do NOT loop."
- The Claude Code variant also exposes a `/board-manager` slash command for direct single-WI operations bypassing the cycle budget; the Copilot variant routes all board operations through the `PM-Team` chat mode (which can choose to delegate via the `agent` tool when appropriate).
