# Assistant-Wizard — Claude Code variant

Installable form of Assistant-Wizard for use in Claude Code. Packaged as a Claude Code plugin that bundles the Assistant-Wizard **skill**.

Assistant-Wizard is implemented as a skill (not a subagent) because its workflow is interview-driven and iterative — the right primitive shape for that pattern.

## Install

### Option A — as a Claude Code plugin (recommended)

From a Claude Code session:

```
/plugin install <absolute-path>/packages/assistant-wizard/claude-code
```

This registers the plugin (defined in `.claude-plugin/plugin.json`) and exposes the bundled skill.

### Option B — as a project-local skill (single directory)

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
