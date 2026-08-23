# Project Lead — Claude Code variant

Installable Claude Code plugin bundling one skill (`project-lead`) and one slash
command (`/project-lead`). The Project Lead is the stakeholder-facing
orchestrator: it owns requirements (as official repo docs), keeps a Project
Memory wiki and a linked GitHub Project Kanban current, and delivers by **guided
handoff** to the `pm-team` and `dev-team` plugins. It never writes specs or code
itself.

## Install

### Option A — via the maruti marketplace (recommended)

Two-step flow from a Claude Code session in the target repo, no local checkout
required:

```
/plugin marketplace add satishc-dev/maruti
/plugin install project-lead@maruti
```

The marketplace manifest lives at `.claude-plugin/marketplace.json` in the maruti
repo root. The first command is one-time per machine; the marketplace stays
registered across sessions.

To pin the marketplace to a specific tag or branch:

```
/plugin marketplace add satishc-dev/maruti@<tag-or-branch>
```

### Option B — from a local checkout

```
/plugin install <absolute-path>/packages/project-lead/claude-code
```

### Option C — project-local copy

```bash
mkdir -p .claude/commands .claude/skills/project-lead
cp packages/project-lead/claude-code/commands/*.md          .claude/commands/
cp packages/project-lead/claude-code/skills/project-lead/*  .claude/skills/project-lead/
```

## Prerequisites

| Integration | Setup |
|---|---|
| GitHub | `gh auth login` for the org/repo where issues, PRs, and the Project live. Needed for the Kanban, the Requirement issue/label, and sub-issues. |
| pm-team | Install `pm-team@maruti` — the Lead hands approved requirements to it for spec work. |
| dev-team | Install `dev-team@maruti` — the Lead hands work items to it for implementation. |
| Obsidian (optional) | Open the `.project-memory/` folder to browse the Lead's wiki, graph view, and logs. |

## What the Lead does

1. **Bootstrap** (`/project-lead bootstrap`) — idempotently scaffolds
   `.project-memory/` (the wiki) and `docs/requirements/` (official requirement
   docs), detects/creates+links a GitHub Project Kanban, detects the Requirement
   issue type (or ensures a `requirement` label), checks that `pm-team`/`dev-team`
   are available, and writes a pointer into `AGENTS.md`/`CLAUDE.md`.
2. **Intake** (`/project-lead` + a need) — captures a requirement as an official
   `docs/requirements/REQ-NNN.md` doc. Two paths: you author a short doc/notes
   (the Lead formalizes it), or you brainstorm the vision (the Lead drafts it).
   Drives it to the Definition of Ready.
3. **Approve** (`/project-lead approve REQ-NNN`) — opens a **requirement PR**;
   your approve/merge is the official signoff (express in-chat signoff available
   for tiny edits). The Lead then creates the **Requirement issue** and moves the
   board to **Ready for Spec**. The Lead will not engage `pm-team` before this.
4. **Guided handoff** — for approved requirements, the Lead launches/recommends
   `/pm-team <requirement>`; after the spec PR merges it links pm-team's
   Feature/Story issues as **sub-issues** of the Requirement issue, then
   recommends `/dev-team <issue>` per child. It reconciles every outcome back into
   memory + the Kanban.
5. **Status / sync / lint** — `/project-lead status` reports the
   requirements→delivery funnel; `sync` reconciles the board with reality; `lint`
   health-checks the memory wiki.

## Usage

```
# One-time per repo
/project-lead bootstrap

# Bring a need to the Lead (brainstorm or hand it a short doc)
/project-lead I want users to be able to export their data as CSV
/project-lead requirement new

# Approve a requirement (opens the requirement PR / records signoff)
/project-lead approve REQ-001

# Hand the approved requirement to the teams (guided)
/pm-team <the Lead will pass the approved problem + acceptance criteria>
/dev-team <child-issue-id>

# Stakeholder views
/project-lead status
/project-lead sync
/project-lead lint
```

## Artifacts the Lead maintains

| Path | Purpose |
|---|---|
| `docs/requirements/` | Official, versioned, PR-reviewable requirement docs + register |
| `.project-memory/` | The Lead's Obsidian-readable wiki (overview, index, log, wiki pages) |
| GitHub Project (v2) | The stakeholder Kanban (Intake → … → Done) |
| Requirement issue + sub-issues | GitHub-native Requirement → Feature → Story traceability |

The full memory layout, requirement doc schema, lifecycle, Definition of Ready,
and approval contract are documented in [`../MEMORY-SCHEMA.md`](../MEMORY-SCHEMA.md).

## Boundaries

The Project Lead **never** writes product code or specs and **never** bypasses
the signoff gates of `pm-team` or `dev-team`. It is the coordinator and the
keeper of durable project context — the work is done by the teams.
