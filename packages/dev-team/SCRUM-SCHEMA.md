# Scrum Schema

This document defines the on-disk Scrum schema that orchestrators in this repository use to plan, journal, retrospect, and accumulate lessons across projects. It is intentionally team-agnostic — the same schema is used by every Scrum-aware orchestrator package shipped from this monorepo.

The schema lives in the **consumer repo's working directory** (the repo where the orchestrator is invoked), never inside the package directory.

## Directory layout

```
.scrum/
├── lessons.md                              # cross-project, 5KB FIFO
└── <project-slug>/
    ├── plan.md                             # frozen plan after user signoff
    ├── design.md                           # OPTIONAL — written only if design review is enabled
    ├── retrospective.md                    # written at project end
    └── agents/
        ├── team-lead.md                    # orchestrator's journal
        ├── software-developer-1.md         # one file per persistent agent identity
        ├── software-developer-2.md
        ├── code-reviewer-1.md
        └── ...
```

- `<project-slug>` is derived by the orchestrator from the work-item title (kebab-case, 3–6 words).
- One file per **persistent agent identity** (e.g., `software-developer-1.md`, `software-developer-2.md`). Identities are stable across cycles — the same `software-developer-1` is re-dispatched cycle after cycle and accumulates history in its own file.
- The orchestrator's journal (`team-lead.md`) sits next to subagent journals under `agents/`.
- The orchestrator is the **SOLE writer** to every file under `agents/`. Subagents emit their work-log entry as the final block of their response text; the orchestrator parses that block and prepends it to the appropriate agent file. This eliminates concurrent-write hazards.

## Work-log entry schema

Each entry written into any file under `agents/` MUST conform to this format. Newest entry on top.

```markdown
## [Cycle <N>] <taskId> · <ISO8601 timestamp UTC>

- **agentId:** <agent-id>
- **taskId:** <task-id>
- **taskName:** <task-name>
- **taskDescription:** <task-description>
- **requirement:** <requirement-ref or "n/a">
- **cycle:** <project-cycle-number>
- **status:** <in-progress | blocked | done | observation>

### Details
**Done** — <bulleted list of what was completed this turn>
**Doing** — <what is in-flight / will be next turn>
**Blockers** — <none | description with concrete unblock ask>
**ETA** — <cycles remaining estimate, or "complete">
```

Field notes:

- `agentId` matches the filename stem (e.g., `software-developer-1` for `software-developer-1.md`). The orchestrator's own entries use `team-lead-1`.
- `status` values:
  - `in-progress` — work continues next cycle; turn budget hit or work not yet complete.
  - `blocked` — cannot proceed without external input; Blockers field MUST contain a concrete unblock ask.
  - `done` — task is complete this cycle.
  - `observation` — used by the orchestrator for cycle summaries; `taskId` is `cycle-<N>-observation`.
- `requirement` is an acceptance-criterion reference (e.g., `AC-1`, `AC-3`) or `n/a`.
- The `Details` section is required even on `blocked` or partial completion — at minimum, fill the fields with concrete content; do not write "n/a" or leave them empty unless truly nothing applies.

## Cycle budget contract

- **Default budget:** 12 cycles.
- **Warn threshold:** at cycle `budget - 2` (default 10), the orchestrator emits a warning to the user with the current status and offers: continue without extending, revise plan, or abort.
- **Hard halt:** at cycle `budget` (default 12), the orchestrator HALTS before dispatching a new cycle. It asks the user one question with three choices:
  1. **Continue (+N cycles)** — extend the budget by N (user-supplied) and resume.
  2. **Abort** — stop the project; jump straight to the retrospective with the project marked as aborted.
  3. **Finalize** — stop the loop with current state; jump to the retrospective with current state as final.
- **Override:** the budget is configurable per invocation via `--cycles N`. `N` MUST be an integer `>= 3`. Smaller values are rejected; the orchestrator falls back to the default.
- The cycle counter starts at `1`, increments by `1` per scrum pass, and **never resets** within a project.

## Governance policies

Scrum-aware orchestrators enforce a standing set of governance policies on every project, automatically, without waiting for a human nudge. They encode the interventions a supervisor would otherwise make by hand — scope creep, mechanical looping, and silent hangs. They are **additive**: they never weaken the plan-signoff, design-signoff, or reviewer gates.

- **Scope-bounds validation.** A task's `validationScope` MUST match its `changeScope`. A `local` change (confined to one package; no shared/public interface, schema, or cross-package contract touched) runs `targeted` validation — the touched package's tests + type-check/lint only, never the full-repo matrix. Only a `cross-cutting` change (shared/app-wide construct, or >1 package boundary) may set `full`. The orchestrator MUST reject any plan that runs full-repo validation for a `local` task.
- **Per-task budget.** Every dispatched task carries `cycleTurnBudget` (tool calls/turn, default 30) plus a soft wall-clock expectation. On breach the worker returns a targeted result or an explicit blocker — never open-ended broad work. A worker still running at 2× budget is treated as a blocker and stopped.
- **Permission allowlist.** Routine safe operations (read files; run tests/linters/type-checks; `git status`/`diff`/`log`/`add`/`commit` on the task sub-branch; `.scrum/` artifacts; targeted builds) are pre-approved and never prompt. Blocker-only operations (force-push; history rewrite; deleting anything outside task scope; secret access; spending money / paid APIs; publishing/releasing) are surfaced as blockers, never performed unattended.
- **Standing auto-intervention.** When a budget / loop / heartbeat signal trips, the orchestrator diagnoses, halts the broad work, re-scopes to targeted validation (or raises a blocker), and records the intervention — governed by the autonomy knob below.
- **Autonomy knob.** `--autonomy <auto-intervene|pause-and-ping>` (default `auto-intervene`, velocity-first) is the single human dial. It governs only budget / loop / heartbeat responses (act immediately vs. ask first); it never overrides the permission allowlist — blocker-only operations always pause for the human.

## Lessons memory (`.scrum/lessons.md`)

The lessons file is a **cross-project** scratch-pad of project-agnostic guidance distilled from each retrospective. It is read at the start of every new project (Phase 0) so future plans can learn from prior runs.

Rules:

- **Cap:** 5 KB (5120 bytes).
- **Order:** newest on top, oldest on bottom (prepend on write).
- **FIFO eviction:** after each prepend, if the file exceeds 5 KB, trim from the bottom until under the cap. Lessons are evicted **whole** — never split a lesson across the trim boundary. If a single lesson is larger than the cap, drop it entirely rather than truncate it mid-content.
- **Lesson shape:** 1–2 lines of guidance + optional `**Why:** ...` follow-up. Each lesson MUST include a `[[<source-project-slug>]]` backlink so a reader can trace it back to the retrospective that produced it.
- **Project-agnostic content:** lessons should describe guidance that likely applies to FUTURE projects, not specifics of the project that produced them. "Always run linters before claiming done" is a lesson; "Refactor `foo.py`" is not.

Example entry:

```markdown
- Always confirm test runner discovery before claiming green CI. **Why:** missed pyproject vs Makefile divergence cost 2 cycles. [[fix-checkout-typos]]
```

## Retrospective format (`.scrum/<project-slug>/retrospective.md`)

Written once, at project end, after the cycle loop exits (whether by success, abort, or finalize). The orchestrator synthesizes it from every file under `.scrum/<project-slug>/agents/*.md`.

Required sections (in order):

1. **What went well** — concrete moments where the plan, dispatch, or execution worked as intended.
2. **What went poorly** — friction points, miscommunications, wasted cycles.
3. **Blockers encountered + resolution** — what stalled the project, what unblocked it.
4. **Cycle budget consumption** — `<used> of <budget>` plus 1–2 sentences on pacing.
5. **Surprises** — anything outside the plan: new constraints discovered, behaviors that needed redesign mid-stream.
6. **Distilled lessons** — 1–3 bullets, each in the form that will be appended to `.scrum/lessons.md`. Include the `[[<project-slug>]]` backlink in each.

After writing the retrospective, the orchestrator appends the distilled lessons (prepended, newest on top) to `.scrum/lessons.md` and applies the FIFO trim.

## Plan format (`.scrum/<project-slug>/plan.md`)

Written once, at the start of the project, and frozen after user signoff. Re-signoff is required if the orchestrator amends the plan during execution.

Required sections:

- **Project slug** — the derived slug.
- **Objective** — one-sentence summary of the work-item goal.
- **Team composition** — list of agent identities the orchestrator will spawn. Each row: `agentId`, `role`, `responsibility` (1 sentence).
- **Task breakdown** — list of tasks. Each row: `taskId` (`task-<n>`), `taskName`, `taskDescription` (1–2 sentences), `requirementRef` (acceptance-criterion id or n/a), `assignedAgentId`, `changeScope` (`local` | `cross-cutting`), `validationScope` (`targeted` | `full`), `successCriteria`. `validationScope` MUST be `targeted` for a `local` task (see [Governance policies](#governance-policies)).
- **Cycle budget** — the cap `N` and warn threshold `N-2`.
- **Definition of done at the project level** — when does the orchestrator declare success?
- **Risks anticipated** — 1–4 risks / blockers anticipated.
- **Lessons applied** — zero or more bullets from `.scrum/lessons.md` that influenced this plan, each linked with `[[<source-project-slug>]]`.

The plan is presented to the user IN CHAT before any subagent is dispatched. The orchestrator MUST NOT proceed until the user explicitly approves.

## Design review mode

Some changes are large enough to justify a Dev Design review and signoff BEFORE implementation kicks off; others (typos, isolated bug fixes, copy tweaks) are not. The orchestrator MUST honor a per-invocation **design-review mode** that controls whether a Dev Design Doc is produced and gated on user signoff.

- **Modes** (passed via `--design <mode>` on invocation; default `auto`):
  - `auto` — orchestrator evaluates complexity signals during planning and RECOMMENDS `yes` or `no`, then asks the user to confirm before either authoring the doc or skipping. The user has the final say.
  - `required` — design doc + signoff are mandatory regardless of complexity signals.
  - `skip` — design doc is never produced; the orchestrator proceeds straight from plan signoff to journal init.
- **Complexity signals** the orchestrator weighs in `auto` mode (RECOMMEND `yes` if any two or more fire):
  1. Task count `>= 3` in the approved plan.
  2. New modules / components / public interfaces (vs. only edits to existing code paths).
  3. Schema or data-model changes (DB migration, API contract change, on-disk format change).
  4. Ambiguity in the work item's acceptance criteria that required orchestrator inference.
  5. Cross-cutting change touching more than one subsystem or package boundary.
  6. Security, auth, or concurrency surface area touched.
- The orchestrator MUST state which signals fired (or "none") when it surfaces its `auto`-mode recommendation.

## Design document format (`.scrum/<project-slug>/design.md`)

Written only when design review is enabled. Frozen after user signoff. Re-signoff is required if the orchestrator amends the design during execution.

Required sections (in order):

1. **Project slug + work-item reference** — slug and a back-link to the work item id/title.
2. **Architectural overview** — 1–3 paragraphs summarizing the approach. Inline a small component / data-flow sketch where useful (ASCII or fenced mermaid).
3. **Components touched** — list of modules / files / services that will be created, modified, or deleted. Mark each as `[new]`, `[edit]`, or `[delete]`.
4. **Interfaces & contracts** — function signatures, API endpoints, message schemas, CLI flags, or other public surfaces being added or changed. Backward-compatibility notes where relevant.
5. **Data model / schema changes** — DB tables, migration steps, on-disk formats, or "n/a".
6. **Alternatives considered** — 1–3 alternative approaches and the one-line reason each was rejected.
7. **Testing strategy** — unit / integration / e2e split; new test files; how the reviewer will verify each acceptance criterion.
8. **Risks & mitigations** — design-level risks (NOT execution risks — those live in `plan.md`).
9. **Open questions** — explicit asks for the user. If non-empty, signoff cannot complete until these are resolved.

The design doc is presented to the user IN CHAT (full content, not just a path) before Phase 3 begins. The orchestrator MUST NOT initialize the Scrum journal, create the feature branch, or dispatch any subagent until the user explicitly approves the design (or chooses `skip` after the orchestrator's `auto` recommendation).
