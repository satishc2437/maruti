# MCP-Tool-Architect

A custom agent that turns a problem statement into a decision-ready MCP tool architecture and writes durable spec/guardrails/success-criteria docs.

## What it does

When invoked, MCP-Tool-Architect runs a focused requirements interview, picks architecture defaults, and writes three documents under `mcp-tools/<tool-name>/specs/product-docs/`:

- `requirements.md`
- `engineering-guardrails.md`
- `success-criteria.md`

It does **not** implement the tool. It produces the artifacts an implementer (or implementation-planner subagent) needs to proceed without ambiguity.

## Install

**Claude Code** — from a Claude Code session in the target repo:

```
/plugin marketplace add satishc-dev/maruti
/plugin install mcp-tool-architect@maruti
```

**GitHub Copilot CLI** — from a Copilot CLI session in the target repo:

```
copilot plugin marketplace add satishc-dev/maruti
copilot plugin install mcp-tool-architect@maruti
```

## Layout of this package

```
packages/mcp-tool-architect/
├── README.md              # this file
├── claude-code/           # installable Claude Code plugin (skill)
│   ├── .claude-plugin/
│   │   └── plugin.json
│   ├── skills/
│   │   └── mcp-tool-architect/
│   │       └── SKILL.md
│   └── README.md
└── github-copilot/        # installable Copilot CLI plugin (chat mode)
    ├── agents/
    │   └── mcp-tool-architect.agent.md
    └── README.md
```

The `claude-code/` and `github-copilot/` subdirectories are **independently installable**. See their READMEs for install steps.
