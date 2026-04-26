# MCP-Tool-Architect — Claude Code variant

Installable form of MCP-Tool-Architect for use in Claude Code. Packaged as a Claude Code plugin that bundles the MCP-Tool-Architect **skill**.

MCP-Tool-Architect is implemented as a skill (not a subagent) because its workflow is interview-driven and iterative — the right primitive shape for that pattern.

## Install

### Option A — as a Claude Code plugin (recommended)

From a Claude Code session:

```
/plugin install <absolute-path>/packages/mcp-tool-architect/claude-code
```

This registers the plugin (defined in `.claude-plugin/plugin.json`) and exposes the bundled skill.

### Option B — as a project-local skill (single directory)

```bash
mkdir -p .claude/skills
cp -r packages/mcp-tool-architect/claude-code/skills/mcp-tool-architect .claude/skills/
```

The skill is then available via `/mcp-tool-architect` or proactive invocation.

## Usage

In a Claude Code session, invoke directly:

```
/mcp-tool-architect
```

Or describe what you want to build and Claude will trigger the skill proactively:

```
I need to design a new MCP tool that <problem statement>.
```

The architect will run a focused requirements interview and write the three primary docs under `mcp-tools/<tool-name>/specs/product-docs/`.
