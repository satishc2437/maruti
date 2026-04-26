# MCP-Tool-Architect — GitHub Copilot variant

Installable form of MCP-Tool-Architect for use as a GitHub Copilot agent mode.

## Install

```bash
mkdir -p .github/agents
cp packages/mcp-tool-architect/github-copilot/agents/mcp-tool-architect.agent.md .github/agents/
```

In VS Code with GitHub Copilot Chat, the agent will appear in the chat-mode picker as **MCP-Tool-Architect**.

## Usage

1. Open Copilot Chat.
2. Switch the chat mode to **MCP-Tool-Architect**.
3. State the problem the new MCP tool should solve.

The architect will run a focused requirements interview and write the three primary docs under `mcp-tools/<tool-name>/specs/product-docs/`.
