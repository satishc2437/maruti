# MCP-Tool-Architect

A custom agent that turns a problem statement into a decision-ready MCP tool architecture and writes durable spec/guardrails/success-criteria docs.

## What it does

When invoked, MCP-Tool-Architect runs a focused requirements interview, picks architecture defaults, and writes three documents under `mcp-tools/<tool-name>/specs/product-docs/`:

- `requirements.md`
- `engineering-guardrails.md`
- `success-criteria.md`

It does **not** implement the tool. It produces the artifacts an implementer (or implementation-planner subagent) needs to proceed without ambiguity.

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
└── github-copilot/        # installable Copilot payload (chat mode)
    ├── packages/
    │   └── mcp-tool-architect.agent.md
    ├── install.sh
    ├── install.ps1
    └── README.md
```

The `claude-code/` and `github-copilot/` subdirectories are **independently installable**. See their READMEs for install steps.
