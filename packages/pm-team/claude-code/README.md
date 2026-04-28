# PM Team — Claude Code variant

Installable Claude Code plugin bundling one skill (`pm-team`), three subagents (`requirements-analyst`, `spec-reviewer`, `board-manager`), and two slash commands (`/pm-team`, `/board-manager`).

## Install

### Option A — via the maruti marketplace (recommended)

Two-step flow from a Claude Code session in the target repo, no local checkout required:

```
/plugin marketplace add satishc2437/maruti
/plugin install pm-team@maruti
```

The marketplace manifest lives at `.claude-plugin/marketplace.json` in the maruti repo root and registers all available plugins. The first command is one-time per machine; the marketplace stays registered across sessions.

To pin the marketplace to a specific tag or branch (rather than the default branch), add a ref suffix:

```
/plugin marketplace add satishc2437/maruti@<tag-or-branch>
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

## Usage

### Start a new initiative

```
/pm-team I want a way to detect duplicate customer accounts
```

The skill will:

1. Conduct an interactive interview (≥3 rounds: scope, non-goals, constraints).
2. Decompose the intent into 2–5 features.
3. Spawn `requirements-analyst` subagents in parallel — one per feature — each producing `docs/specs/<initiative-slug>/<feature-slug>.md`.
4. Run `spec-reviewer` (auto-iterate up to 3 times on no-go).
5. Commit specs to branch `users/satishc/specs/<initiative-slug>` and open a **spec PR**.
6. Stop and wait for your review.

### After PR review — comments to address

```
/pm-team feedback 1234
```

Fetches PR #1234 comments, dispatches `requirements-analyst`s to revise the affected specs, re-runs `spec-reviewer`, pushes to the same branch. Re-review.

### After PR review — approved

```
/pm-team approved 1234
```

Verifies PR #1234 is merged (asks you to merge if not). Then dispatches `board-manager` to create the parent + child WIs on the board. Reports WI URLs; you handoff to `dev-team` per item:

```
/dev-team 5678
```

### Direct board operations (no PM flow)

```
/board-manager create a User Story for "audit log retention" with acceptance criteria X, Y, Z
/board-manager update WI 1234: set state to In Progress
/board-manager list all unassigned User Stories in the current sprint
```

The platform (ADO vs GitHub) is auto-detected from `git remote get-url origin` — pass `--platform <ado|gh>` only if the repo has ambiguous remotes.
