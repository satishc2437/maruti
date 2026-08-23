# Project-Lead — GitHub Copilot variant

Installable form of Project Lead for GitHub Copilot CLI as a custom chat-mode
agent. Same lifecycle and guardrails as the Claude Code variant: it owns
requirements (as official repo docs), keeps a Project Memory wiki and a linked
GitHub Project Kanban current, and delivers by **guided handoff** to the
`PM-Team` and `Dev-Team` agents. It never writes specs or code itself.

## Install

From a Copilot CLI session in the target repository:

```
copilot plugin marketplace add satishc-dev/maruti
copilot plugin install project-lead@maruti
```

The first command is one-time per machine; subsequent installs only need the
second line.

## Manual install

If you prefer to vendor the agent directly into a repo (no plugin system):

```bash
mkdir -p .github/agents
cp agents/project-lead.agent.md .github/agents/project-lead.agent.md
```

Copilot CLI also reads `~/.copilot/agents/` for personal-scope agents if you want
it available across all your projects.

## Prerequisites

| Integration | Setup |
|---|---|
| GitHub | `gh auth login` for the org/repo where issues, PRs, and the Project live. |
| PM-Team | Install `pm-team@maruti` — the Lead hands approved requirements to it for spec work. |
| Dev-Team | Install `dev-team@maruti` — the Lead hands work items to it for implementation. |
| Obsidian (optional) | Open the `.project-memory/` folder to browse the Lead's wiki and logs. |

## Usage

Once installed, switch to the **Project-Lead** agent in your Copilot CLI session.
(When dispatching headlessly via `copilot -p ... --agent <id>`, the agent id is
plugin-namespaced: `project-lead:project-lead` — likewise `pm-team:pm-team` and
`dev-team:dev-team`.)

```
# One-time per repo
@project-lead bootstrap

# Bring a need to the Lead (brainstorm, or hand it a short doc)
@project-lead I want users to be able to export their data as CSV
@project-lead requirement new

# Approve a requirement (opens the requirement PR / records signoff)
@project-lead approve REQ-001

# Hand the approved requirement to the teams (guided)
@pm-team <the Lead passes the approved problem + acceptance criteria>
@dev-team <child-issue-id>

# Stakeholder views
@project-lead status
@project-lead sync
@project-lead lint
```

The Project-Lead agent:

1. **Bootstraps** the repo — scaffolds `.project-memory/` (the wiki) and
   `docs/requirements/` (official requirement docs), detects/creates+links a
   GitHub Project Kanban, detects the Requirement issue type (or ensures a
   `requirement` label), checks `PM-Team`/`Dev-Team` availability, and writes a
   pointer into `AGENTS.md`/`CLAUDE.md`.
2. **Captures requirements** as official `docs/requirements/REQ-NNN.md` docs —
   either by formalizing a short doc/notes you provide, or by brainstorming the
   vision and drafting it for you. Drives each to the Definition of Ready.
3. **Approves** via a **requirement PR** (your approve/merge is the official
   signoff; express in-chat signoff available for tiny edits), then creates the
   **Requirement issue** and moves the board to Ready for Spec. It will not engage
   PM-Team before this gate.
4. **Hands off** approved requirements to PM-Team (spec), links the resulting
   Feature/Story issues as **sub-issues** of the Requirement issue for
   traceability, then hands child issues to Dev-Team (build) — reconciling every
   outcome back into memory + the Kanban.
5. **Reports** the requirements→delivery funnel on demand and keeps the board in
   sync.

The tracker platform (GitHub vs Azure DevOps) is auto-detected from
`git remote get-url origin`. On non-GitHub remotes the Lead degrades gracefully
(memory + requirement docs + guided handoff still work; Kanban uses ADO Boards).

The full memory layout, requirement doc schema, lifecycle, Definition of Ready,
and approval contract are documented in [`../MEMORY-SCHEMA.md`](../MEMORY-SCHEMA.md).

## Notes vs. the Claude Code variant

The two variants share the same lifecycle, the same `.project-memory/` and
`docs/requirements/` schemas, the same approval gate, and the same guardrails.
The only mechanical differences:

- The Claude Code variant is a **skill** loaded by the `/project-lead` slash
  command and delegates to `/pm-team` and `/dev-team` slash commands.
- The Copilot variant is a single **chat-mode agent** (`Project-Lead`) that
  delegates by dispatching the `PM-Team` and `Dev-Team` agents via the `agent`
  tool, or by recommending you switch to them — always under the same guided
  handoff that respects their own signoff gates.

## Boundaries

The Project Lead **never** writes product code or specs and **never** bypasses
the signoff gates of `PM-Team` or `Dev-Team`. It is the coordinator and the
keeper of durable project context — the work is done by the teams.
