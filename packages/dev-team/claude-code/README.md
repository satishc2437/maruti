# Dev Team — Claude Code variant

Installable Claude Code plugin bundling three subagents (`team-lead`, `software-developer`, `code-reviewer`) and one slash command (`/dev-team`).

## Install

### Option A — as a Claude Code plugin (recommended)

From a Claude Code session:

```
/plugin install <absolute-path>/packages/dev-team/claude-code
```

### Option B — project-local

```bash
mkdir -p .claude/agents .claude/commands
cp packages/dev-team/claude-code/agents/*.md .claude/agents/
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
/dev-team ado 1234
/dev-team gh 42
```

Or invoke the team lead directly:

```
team-lead, please pick up ADO work item 1234
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
