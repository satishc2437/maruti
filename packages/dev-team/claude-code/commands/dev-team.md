---
description: Drive an Azure DevOps work item or GitHub issue through design, parallel implementation, code review, and PR creation under a Scrum cadence. Platform auto-detected from the git remote.
argument-hint: <work-item-id> [--cycles <N>] [--design <auto|required|skip>] [--autonomy <auto-intervene|pause-and-ping>]
---

User arguments: $ARGUMENTS

Trigger the `dev-team` skill, which orchestrates the team end-to-end under a Scrum cadence.

Parse `$ARGUMENTS` as follows:

1. The first positional token is the work-item ID — typically a numeric ID (e.g., `1234`, `42`).
2. Optional flag `--cycles <N>` sets the project cycle budget. `<N>` MUST be an integer `>= 3`. Default is `12`. If the user passes a value below `3`, fall back to the default and warn the user once.
3. Optional flag `--platform <ado|gh>` overrides platform detection; otherwise leave detection to the skill.
4. Optional flag `--design <auto|required|skip>` controls whether a Dev Design Doc is produced and gated on user signoff before implementation. Default is `auto` (the skill recommends yes/no based on complexity signals and asks the user to confirm). `required` forces a design review; `skip` proceeds straight from plan signoff to implementation. Any other value falls back to `auto` with a warning.
5. Optional flag `--autonomy <auto-intervene|pause-and-ping>` sets how the orchestrator responds when a governance signal (budget / loop / heartbeat) trips. Default is `auto-intervene` (diagnose, halt, and re-scope immediately). `pause-and-ping` halts and asks the user first. It never relaxes the permission allowlist — dangerous operations always pause. Any other value falls back to `auto-intervene` with a warning.

If `$ARGUMENTS` is empty or unparseable as a work-item ID, ask the user to re-issue the command with an ID.

The platform (Azure DevOps vs GitHub) is auto-detected from `git remote get-url origin`. Don't ask the user to specify it unless detection is ambiguous; if the user passed `--platform <ado|gh>` in `$ARGUMENTS`, honor it.

Do not perform the workflow yourself in the main agent — load and execute the `dev-team` skill, which has the full Scrum-cadence workflow: Phase 0 (read `.scrum/lessons.md`), Phase 1 (fetch the work item), Phase 2 (plan + explicit user signoff before any subagent is dispatched), Phase 2.5 (OPTIONAL Dev Design Doc + signoff — gated by `--design <auto|required|skip>`), Phase 3 (initialize Scrum journal and branch/worktrees), Phase 4 (cycle loop dispatching `software-developer` subagents in parallel via `Task` + `run_in_background: true` and `code-reviewer` sequentially), Phase 5 (retrospective + lessons FIFO), Phase 6 (ship the PR), Phase 7 (final report).
