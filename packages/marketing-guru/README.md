# marketing-guru

A proactive MBA-grade marketing advisor persona for use during an MBA Marketing Management course simulation, framed around running and growing a **bike company** and beating the competition.

Ships as a **Skill** for both **Claude Code** and **GitHub Copilot CLI** — same byte-identical body, activates proactively on marketing/strategy topics.

## Layout

```
packages/marketing-guru/
├── README.md                                          # this file
├── claude-code/                                       # installable Claude Code plugin
│   ├── .claude-plugin/plugin.json                     # plugin manifest
│   ├── skills/marketing-guru/SKILL.md                 # the skill body
│   └── README.md                                      # Claude Code install + usage
└── github-copilot/                                    # installable Copilot CLI plugin
    ├── skills/marketing-guru/SKILL.md                 # the skill body (byte-identical)
    └── README.md                                      # Copilot CLI install + usage
```

## Install

**Claude Code** — from a Claude Code session in the target repo:

```
/plugin marketplace add satishc-dev/maruti
/plugin install marketing-guru@maruti
```

**GitHub Copilot CLI** — from a Copilot CLI session in the target repo:

```
copilot plugin marketplace add satishc-dev/maruti
copilot plugin install marketing-guru@maruti
```

See [`claude-code/README.md`](claude-code/README.md) and [`github-copilot/README.md`](github-copilot/README.md) for manual-vendor alternatives.

## Behavior at a glance

- **Trigger**: any marketing strategy, performance, positioning, or simulation conversation. Activates without being asked.
- **Style**: Socratic first (≤3 sharp questions), directive when you ask for a call.
- **Frameworks**: STP, 4Ps/7Ps, Porter's Five Forces, Ansoff, BCG, Brand Pyramid, Customer Journey, JTBD — one or two per decision.
- **Data discipline**: never invents market numbers. Reads simulation files from the working folder; will use a connected Playwright MCP server **read-only** to browse the live simulation UI. Never modifies simulation state.
