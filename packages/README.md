# Custom agent packages

This directory is the canonical source for the custom agent packages that
Maruti produces — bundles of Claude Code and GitHub Copilot CLI customizations.
Each package lives in its own folder under `packages/<name>/` with a
**platform-bifurcated** layout. Each platform may host any combination of
primitives — Claude Code supports subagents, skills, and slash commands;
GitHub Copilot CLI supports custom agents (chat modes), skills, and prompt files.

Both platform variants are installable as **plugins** via the corresponding
maruti marketplace manifest at the repo root
([`.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json) for
Claude Code, [`.github/plugin/marketplace.json`](../.github/plugin/marketplace.json)
for Copilot CLI).

```
packages/<name>/
├── README.md                            # top-level: purpose, layout, links
├── claude-code/                         # installable Claude Code plugin
│   ├── .claude-plugin/plugin.json       # always (plugin manifest)
│   ├── agents/*.md                      # zero or more subagents
│   ├── skills/*/SKILL.md                # zero or more skills
│   ├── commands/*.md                    # zero or more slash commands
│   └── README.md                        # install / usage
└── github-copilot/                      # installable Copilot CLI plugin
    ├── agents/*.agent.md                # zero or more custom agents (chat modes)
    ├── skills/*/SKILL.md                # zero or more skills
    ├── prompts/*.prompt.md              # zero or more prompt files
    └── README.md                        # install / usage
```

A package may ship multiple primitives in the same class — e.g. a coordinated
team of subagents that delegate to each other (see [`dev-team/`](dev-team/)).
Filenames must be unique per primitive class across **all** packages, since
the publish target preserves the source filename.

The right primitive for a given package depends on its intent. The
[`assistant-wizard/`](assistant-wizard/) package picks one for you and explains
why, based on a short interview.

Naming conventions:

- The **package directory name** is lowercase-hyphen (e.g. `assistant-wizard`).
- The **Claude Code primitive `name:`** (subagent, skill) is lowercase-hyphen.
- The **Copilot chat mode `name:`** is TitleCase-Hyphen (e.g. `Assistant-Wizard`).
- When the same narrative content (skill body, chat mode body) appears in both
  the Claude Code and Copilot variants of one package, it is **byte-identical**;
  only frontmatter differs.

Either platform variant is optional. A package targeting only Claude Code
omits the `github-copilot/` subdirectory, and vice versa.

## Where these packages get used

The agents authored here are intended for use in **other** repositories where
you want Copilot or Claude Code to load a custom agent. Maruti is the source
of truth; consuming repos pull in whatever subset they need.

This repo also publishes a **symlink mirror** so its own Claude Code and
Copilot can use the agents during work on Maruti itself:

| Source | Mirror |
|---|---|
| `packages/<name>/claude-code/agents/<file>.md` | `.claude/agents/<file>.md` |
| `packages/<name>/claude-code/skills/<dir>/` | `.claude/skills/<dir>/` |
| `packages/<name>/claude-code/commands/<file>.md` | `.claude/commands/<file>.md` |
| `packages/<name>/github-copilot/agents/<file>.agent.md` | `.github/agents/<file>.agent.md` |
| `packages/<name>/github-copilot/prompts/<file>.prompt.md` | `.github/prompts/<file>.prompt.md` |

Source filenames are preserved; one mirror is created per artifact found.

The mirror is managed by [`scripts/link_packages.py`](../scripts/README.md)
and is enforced by CI — never edit anything under `.claude/` or
`.github/agents/` directly; edit the source under `packages/<name>/`.

## Authoring a new agent

The recommended path is to use the [`assistant-wizard/`](assistant-wizard/)
package itself: it asks for the target environment(s), captures your intent,
recommends the right primitive per environment, and emits the package layout
above.

If authoring by hand:

1. Create `packages/<new-name>/` with the layout above. Include only the
   primitive(s) you need.
2. Run the mirror sync from the repo root:
   ```bash
   python scripts/link_packages.py sync
   ```
3. Commit `packages/<new-name>/` and the new symlinks under `.claude/` and/or
   `.github/` together.

CI runs `python scripts/link_packages.py check` on every PR; if the symlinks
drift from the source, the build fails.

## Consuming these packages from another repo

**Claude Code** — install via the [marketplace manifest](../.claude-plugin/marketplace.json) at the repo root. Two-step flow, both run from a Claude Code session in the target repo:

```
/plugin marketplace add satishc-dev/maruti
/plugin install <name>@maruti
```

Where `<name>` is one of `pm-team`, `dev-team`, `assistant-wizard`, `mcp-tool-architect`, `marketing-guru`, `project-lead`. The first command is one-time per machine; subsequent installs only need the second line.

If you already have maruti cloned locally, you can install a single plugin from the path instead:

```
/plugin install <absolute-path>/packages/<name>/claude-code
```

**GitHub Copilot CLI** — install via the [marketplace manifest](../.github/plugin/marketplace.json) at the repo root. Two-step flow, both run from a Copilot CLI session in the target repo:

```
copilot plugin marketplace add satishc-dev/maruti
copilot plugin install <name>@maruti
```

The first command is one-time per machine; subsequent installs only need the second line.

You can also vendor by direct copy — copy the platform variant you need into
the consumer's expected location (e.g. `.github/agents/<name>.agent.md`,
`.github/skills/<name>/SKILL.md`, or `.claude/skills/<name>/`).

## Currently authored agents

All six packages ship variants for both Claude Code and GitHub Copilot CLI.
The Claude Code variant typically uses multiple subagents fanned out by an
orchestrator; the Copilot CLI variant collapses that orchestration into a
single chat-mode agent (or skill) since Copilot's primitive model is flatter.

- [`assistant-wizard/`](assistant-wizard/) — designs and generates new custom
  packages (subagent / skill / slash command / chat mode / prompt file) for
  Claude Code, GitHub Copilot CLI, or both.
- [`mcp-tool-architect/`](mcp-tool-architect/) — turns a problem statement
  into a decision-ready MCP tool architecture and writes the durable
  spec/guardrails/success-criteria docs.
- [`dev-team/`](dev-team/) — multi-agent software development team
  (`team-lead`, `software-developer`, `code-reviewer` subagents plus a
  `/dev-team` slash command on Claude Code; a single `Dev-Team` chat agent on
  Copilot CLI) that drives an Azure DevOps work item or GitHub issue from
  intake through implementation, review, and PR.
- [`pm-team/`](pm-team/) — multi-agent product management team
  (`pm-team` skill + `requirements-analyst`, `spec-reviewer`, `board-manager`
  subagents + `/pm-team` and `/board-manager` slash commands on Claude Code;
  a single `PM-Team` chat agent on Copilot CLI) that gathers intent, produces
  feature specs, opens a spec PR, and on approval seeds the Kanban board with
  WIs ready for `dev-team`.
- [`marketing-guru/`](marketing-guru/) — proactive MBA-grade marketing advisor
  for an MBA bike-company simulation; ships as a skill on both platforms with a
  byte-identical body.
- [`project-lead/`](project-lead/) — stakeholder-facing Project Lead
  (`project-lead` skill + `/project-lead` slash command on Claude Code; a single
  `Project-Lead` chat agent on Copilot CLI) that owns requirements as official
  `docs/requirements/` docs behind an approval gate, maintains a Project Memory
  wiki (`.project-memory/`) plus a linked GitHub Project Kanban, and delivers by
  guided handoff to `pm-team` and `dev-team` — never writing specs or code
  itself.
