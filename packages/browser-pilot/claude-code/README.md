# browser-pilot (Claude Code)

## Install

From a Claude Code session in any repo:

```
/plugin install <path-to-maruti>/packages/browser-pilot/claude-code
```

Or via the maruti marketplace (once published):

```
/plugin marketplace add satishc-dev/maruti
/plugin install browser-pilot@maruti
```

## What it provides

A **skill** (`browser-pilot`) that activates when you mention browsing, web
interaction, Chrome, or visiting a URL. The skill instructs the agent on:

- Which browser-pilot MCP tools to use and in what order
- Best practices for reliable automation (waits, selectors, screenshots)
- Error recovery patterns

## Prerequisites

The `browser-pilot` MCP server must be configured in your MCP client settings.
Add to your Claude Code MCP config:

```json
{
  "mcpServers": {
    "browser-pilot": {
      "command": "npx",
      "args": ["--prefix", "<path-to-maruti>/mcp-tools/browser-pilot", "browser-pilot"]
    }
  }
}
```

Or if published to npm:

```json
{
  "mcpServers": {
    "browser-pilot": {
      "command": "npx",
      "args": ["-y", "browser-pilot"]
    }
  }
}
```
