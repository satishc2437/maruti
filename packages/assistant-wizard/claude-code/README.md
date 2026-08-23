# Assistant-Wizard — Claude Code variant

Installable Claude Code plugin bundling the Assistant-Wizard **skill** plus two helper subagents:

- **`assistant-wizard`** (skill) — orchestrator + intent interview.
- **`wizard-builder`** (subagent) — writes the generated package files from a structured design brief.
- **`wizard-reviewer`** (subagent) — read-only gate that scores the output against a prompt-engineering rubric and returns `go` / `no-go`.

The skill auto-iterates builder ↔ reviewer up to **3 iterations** on `no-go`. This separates the interview context (rich, multi-turn) from generation (clean, brief-driven) and validation (cold, rubric-driven), which produces more effective `SKILL.md` / `agent.md` outputs than a single context could.

## Install

### Option A — via the maruti marketplace (recommended)

Two-step flow from a Claude Code session in the target repo, no local checkout required:

```
/plugin marketplace add satishc-dev/maruti
/plugin install assistant-wizard@maruti
```

The marketplace manifest lives at `.claude-plugin/marketplace.json` in the maruti repo root and registers all available plugins. The first command is one-time per machine; the marketplace stays registered across sessions.

To pin the marketplace to a specific tag or branch (rather than the default branch), add a ref suffix:

```
/plugin marketplace add satishc-dev/maruti@<tag-or-branch>
```

### Option B — from a local checkout

If you already have maruti cloned:

```
/plugin install <absolute-path>/packages/assistant-wizard/claude-code
```

### Option C — project-local skill (single directory)

```bash
mkdir -p .claude/skills
cp -r packages/assistant-wizard/claude-code/skills/assistant-wizard .claude/skills/
```

The skill is then available via `/assistant-wizard` or proactive invocation.

## Usage

In a Claude Code session, invoke directly:

```
/assistant-wizard
```

Or describe what you want to build and Claude will trigger the skill proactively:

```
I want to create a new custom subagent / skill / slash command / chat mode / prompt file for <purpose>.
```

Assistant-Wizard will then ask which target environment(s), capture your intent, recommend the right primitive per environment, and generate a deployable payload at `packages/<new-name>/`.
