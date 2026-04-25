# Agent markdowns

This directory is the canonical source for the agent definitions that
Maruti produces. Each agent lives in its own folder under `agents/<name>/`
with a stable layout:

```
agents/<name>/
├── <name>.agent.md            # the agent definition (frontmatter + body)
└── <name>-internals/          # optional companion assets
    ├── rules.json             # deterministic filesystem/access rules
    └── ReadMe.md              # rationale, design decisions, usage notes
```

The naming convention is **lowercase-hyphen** for the directory and the
markdown filename. The frontmatter `name:` field can use TitleCase-Hyphen
display naming (e.g. `Agent-Builder`, `MCP-Tool-Architect`).

## Where these markdowns get used

The agents authored here are intended for use in **other** repositories
where you want Copilot or Claude Code to load a custom agent. Maruti is
the source of truth; consuming repos pull in whatever subset they need.

This repo also publishes a **symlink mirror** at `.github/agents/` so
this repo's own Copilot can use the agents during work on Maruti itself.
That mirror is managed by [`scripts/link_agents.py`](../scripts/README.md)
and is enforced by CI — never edit anything under `.github/agents/`
directly; edit the source here under `agents/<name>/`.

## Authoring a new agent

1. Create `agents/<new-name>/` with `<new-name>.agent.md` and (optionally)
   `<new-name>-internals/`.
2. Run the mirror sync from the repo root:
   ```bash
   python scripts/link_agents.py sync
   ```
3. Commit `agents/<new-name>/` and the new symlinks under `.github/agents/`
   together.

CI runs `python scripts/link_agents.py check` on every PR; if the symlinks
drift from the source, the build fails.

## Consuming these markdowns from another repo

Three patterns work. Pick whichever fits the consuming repo's preferences.

**Subtree / submodule** — clone Maruti as a git subtree or submodule and
point the consumer's agent loader at this `agents/` directory.

**Direct copy** — copy `agents/<name>/<name>.agent.md` (and the
`<name>-internals/` directory if present) into the consumer's expected
agent location:

- **GitHub Copilot**: `.github/agents/<name>.agent.md` (+ internals).
- **Claude Code**: per the consumer's agent directory layout.

**Vendored snippet** — copy just the body of the markdown into the
consumer's own agent file.

When you upgrade an agent here, propagate the change downstream however
the consumer was set up.

## Currently authored agents

- [`agent-builder/`](agent-builder/) — generates new Copilot agent
  packages by interviewing for archetype and emitting the required files.
- [`fund-selection-advisor/`](fund-selection-advisor/) — interviews the
  user for investment preferences and produces a top-3 fund/ETF shortlist.
- [`mcp-tool-architect/`](mcp-tool-architect/) — turns a problem
  statement into a decision-ready MCP tool architecture and writes the
  durable spec/guardrails/success-criteria docs.
- [`profile-manager/`](profile-manager/) — manages user profile data.
- [`shannon/`](shannon/) — coding partner agent.
