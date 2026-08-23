# Browser Pilot MCP Server

An MCP (Model Context Protocol) server that launches a Chromium-based browser in remote debugging mode and provides full Playwright-based browser automation through a unified interface. Simply say "open fidelity.com and check my watchlist" — no separate browser launch or Playwright configuration needed.

## Features

- **Auto-detects browsers** — Chrome, Edge, Brave, or Chromium (in priority order)
- **Auto-launches** with remote debugging (or connects to an existing instance)
- **Headed mode by default** — watch the browser in action
- **Existing user profile** — stay logged in to your sites
- **17 browser automation tools** exposed via MCP
- **Cross-platform** — Windows, macOS, and Linux support

## Quick Start

### Run from GitHub (npx)

```bash
npx --package="git+https://github.com/satishc-dev/maruti.git#subdirectory=mcp-tools/browser-pilot" browser-pilot
```

### Run locally (development)

```bash
cd mcp-tools/browser-pilot
npm install
npm run build
npm start
```

### Run with tsx (no build required)

```bash
cd mcp-tools/browser-pilot
npm run dev
```

## MCP Client Configuration

### Claude Desktop / Copilot

Add to your MCP settings:

```json
{
  "mcpServers": {
    "browser-pilot": {
      "command": "node",
      "args": ["path/to/mcp-tools/browser-pilot/dist/index.js"]
    }
  }
}
```

### VS Code (Copilot)

Add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "browser-pilot": {
      "command": "node",
      "args": ["${workspaceFolder}/mcp-tools/browser-pilot/dist/index.js"]
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `browser_navigate` | Navigate to a URL |
| `browser_click` | Click an element by CSS selector or text |
| `browser_type` | Type text into an input element |
| `browser_screenshot` | Capture screenshot (full page or element) |
| `browser_get_text` | Get text content of the page or element |
| `browser_scroll` | Scroll page or element in any direction |
| `browser_wait_for` | Wait for selector or load state |
| `browser_evaluate` | Execute JavaScript in page context |
| `browser_select` | Select option from dropdown |
| `browser_upload` | Upload files to file input |
| `browser_cookies` | Get, set, delete, or clear cookies |
| `browser_pdf` | Save page as PDF |
| `browser_back` | Navigate back in history |
| `browser_forward` | Navigate forward in history |
| `browser_close` | Close a tab or the entire browser |
| `browser_tabs` | List all open tabs |
| `browser_switch_tab` | Switch active tab |

## Configuration

The server uses sensible defaults but can be customized per-tool-call:

- **Browser**: Auto-detected in priority order: Chrome > Edge > Brave > Chromium. Override with `chromePath` parameter.
- **Browser profile**: Uses your existing browser profile by default (stay logged in). Pass `useExistingProfile: false` to use a temporary profile.
- **Display**: Headed (visible) by default. Pass `headless: true` for headless mode.
- **Port**: Uses `9222` by default for Chrome DevTools Protocol.

## Architecture

The codebase follows strict OOP principles:

- **Interfaces** (`IBrowserLocator`, `IChromeLauncher`, `IBrowserManager`, `ITool`) define contracts
- **Strategy pattern** for cross-platform browser discovery (Chrome, Edge, Brave, Chromium)
- **Singleton** `BrowserManager` for shared Playwright connection
- **Template Method** in `BaseTool` — subclasses implement `runImpl()`
- **Dependency Injection** — tools receive `IBrowserManager` via constructor
- **Strict TypeScript** — `strict: true`, no `any`, explicit access modifiers

## Development

```bash
# Install dependencies
npm install

# Run tests
npm test

# Run tests with coverage (>95% enforced)
npm run test:coverage

# Type check
npx tsc --noEmit

# Build
npm run build
```

## Requirements

- Node.js >= 18
- A Chromium-based browser installed (Chrome, Edge, Brave, or Chromium — auto-detected)
- No `playwright install` needed — connects to your existing browser via CDP
