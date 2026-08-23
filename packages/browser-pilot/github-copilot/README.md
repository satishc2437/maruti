# browser-pilot (GitHub Copilot)

## Install

From a Copilot CLI session in any repo:

```
copilot plugin install <path-to-maruti>/packages/browser-pilot/github-copilot
```

Or via the maruti marketplace (once published):

```
copilot plugin marketplace add satishc-dev/maruti
copilot plugin install browser-pilot@maruti
```

## What it provides

A **skill** (`browser-pilot`) that activates when you mention browsing, web
interaction, Chrome, or visiting a URL. The skill instructs the agent on:

- Which browser-pilot MCP tools to use and in what order
- Best practices for reliable automation (waits, selectors, screenshots)
- Error recovery patterns

## Prerequisites

The `browser-pilot` MCP server must be configured in your MCP client settings.
Add to your Copilot MCP config:

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
