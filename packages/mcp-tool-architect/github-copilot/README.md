# MCP-Tool-Architect — GitHub Copilot variant

Installable form of MCP-Tool-Architect for use in GitHub Copilot CLI as a custom agent.

## Install

From a Copilot CLI session in the target repository:

```
copilot plugin marketplace add satishc-dev/maruti
copilot plugin install mcp-tool-architect@maruti
```

The first command is one-time per machine; subsequent installs only need the second line.

## Manual install

If you prefer to vendor the agent directly into a repo (no plugin system):

```bash
mkdir -p .github/agents
cp agents/mcp-tool-architect.agent.md .github/agents/mcp-tool-architect.agent.md
```

Copilot CLI also reads `~/.copilot/agents/` for personal-scope agents if you want it available across all your projects.

## Usage

Once installed, switch to the **MCP-Tool-Architect** agent in your Copilot CLI session and state the problem the new MCP tool should solve.

The architect will run a focused requirements interview and write the three primary docs under `mcp-tools/<tool-name>/specs/product-docs/`:

- `requirements.md`
- `engineering-guardrails.md`
- `success-criteria.md`
