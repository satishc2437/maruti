# Dev Team — Claude Code variant

Installable Claude Code plugin bundling three subagents (`team-lead`, `software-developer`, `code-reviewer`) and one slash command (`/dev-team`).

## Install

### Option A — via the maruti marketplace (recommended)

Two-step flow from a Claude Code session in the target repo, no local checkout required:

```
/plugin marketplace add satishc2437/maruti
/plugin install dev-team@maruti
```

The marketplace manifest lives at `.claude-plugin/marketplace.json` in the maruti repo root and registers all available plugins. The first command is one-time per machine; the marketplace stays registered across sessions.

To pin the marketplace to a specific tag or branch (rather than the default branch), add a ref suffix:

```
/plugin marketplace add satishc2437/maruti@<tag-or-branch>
```

### Option B — from a local checkout

If you already have maruti cloned:

```
/plugin install <absolute-path>/packages/dev-team/claude-code
```

### Option C — project-local copy

```bash
mkdir -p .claude/agents .claude/commands
cp packages/dev-team/claude-code/agents/*.md   .claude/agents/
cp packages/dev-team/claude-code/commands/*.md .claude/commands/
```

## Prerequisites

| Integration | Setup |
|---|---|
| Azure DevOps | Install the `azure-devops-mcp` server and configure it with a PAT. The `team-lead` subagent will use `mcp__azure-devops-mcp__*` tools. |
| GitHub | `gh auth login` (or sandbox credential injection) for the org/repo you'll be raising PRs against. |
| Git worktrees | `git` ≥ 2.5 (any modern install). |

## Usage

Kick off a run via the slash command:

```
/dev-team 1234
```

The `team-lead` subagent auto-detects whether `1234` is an Azure DevOps work item or a GitHub issue from `git remote get-url origin`. Override with `--platform <ado|gh>` if your repo has remotes pointing at both.

Or invoke the team lead directly:

```
team-lead, please pick up work item 1234
```

The `team-lead` subagent will:

1. Fetch the work item (title, description, acceptance criteria).
2. Read the repo's `CLAUDE.md` / `README.md` and recent history.
3. Produce a brief design and decompose it into independent tasks.
4. Create a feature branch `users/satishc/feature/<work-item-id>-<slug>` and one worktree per task under `.worktrees/<work-item-id>/`.
5. Spawn `software-developer` subagents in parallel, one per task.
6. Gate the combined result through `code-reviewer` — auto-iterate up to **3 times** on no-go.
7. On go: merge worktrees → push branch → open PR via `az repos pr create` (ADO) or `gh pr create` (GitHub) → delete worktrees.
8. On 3-iteration failure: report back to you with the diff, the reviewer's feedback, and worktrees left in place.
