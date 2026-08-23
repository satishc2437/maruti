# marketing-guru — Claude Code variant

Installable Claude Code plugin bundling one skill (`marketing-guru`) — a proactive MBA-grade marketing advisor for an MBA bike-company simulation. Activates whenever the conversation touches marketing strategy, business performance, competitive positioning, or simulation files in the working folder.

## Install

### Option A — via the maruti marketplace (recommended)

Two-step flow from a Claude Code session in the target repo, no local checkout required:

```
/plugin marketplace add satishc-dev/maruti
/plugin install marketing-guru@maruti
```

The marketplace manifest lives at `.claude-plugin/marketplace.json` in the maruti repo root and registers all available plugins. The first command is one-time per machine; the marketplace stays registered across sessions.

To pin the marketplace to a specific tag or branch (rather than the default branch), add a ref suffix:

```
/plugin marketplace add satishc-dev/maruti@<tag-or-branch>
```

### Option B — from a local checkout

If you already have maruti cloned, install with an **absolute path** (relative paths are resolved against the CWD of the Claude Code session, which is rarely the maruti repo):

```
/plugin install <absolute-path>/packages/marketing-guru/claude-code
```

### Option C — project-local copy

```bash
mkdir -p .claude/skills/marketing-guru
cp packages/marketing-guru/claude-code/skills/marketing-guru/*  .claude/skills/marketing-guru/
```

## Usage

The skill is **proactive** — there is no slash command to invoke. Just start working on simulation files or ask a marketing question, and the guru weighs in. Examples:

- *"Round 3 results just dropped — here's the scorecard. What should I change next round?"* — drop the file in the working folder, the guru reads it and weighs in.
- *"Competitor B undercut us on the e-MTB segment. How should I respond?"* — guru runs ≤3 Socratic questions, then on request gives a directive call grounded in framework + sim data.
- *"Help me think through the STP for the youth segment."* — guru frames the segmentation, asks for the relevant data points, recommends a position once the data is in.

If a Playwright MCP server is connected, the guru will use it **read-only** to navigate the live simulation UI (dashboards, market research, competitor data). It will never click submit/decide/advance buttons or otherwise mutate simulation state.

## What it does

- Activates **proactively** on marketing/strategy topics — you don't need to summon it.
- Defaults to **Socratic** prompting on a new question, switches to a **directive recommendation** the moment you ask for a call.
- Anchors advice in MBA-canonical frameworks (STP, 4Ps/7Ps, Porter's Five Forces, Ansoff, BCG, Brand Pyramid, Customer Journey, JTBD) — one or two per decision, never a textbook dump.
- Reads **your** simulation data — files in the working folder, and (if a Playwright MCP server is connected) the live simulation UI **read-only**. Never invents market numbers. Never modifies simulation state.

## Files

- `.claude-plugin/plugin.json` — plugin manifest
- `skills/marketing-guru/SKILL.md` — the skill body (persona, triggers, operating rules)
