# Custom agent packages

This directory is the canonical source for the custom agent packages that
Maruti produces — bundles of Claude Code and GitHub Copilot customizations.
Each package lives in its own folder under `packages/<name>/` with a
**platform-bifurcated** layout. Each platform may host any combination of
primitives — Claude Code supports subagents, skills, and slash commands;
GitHub Copilot supports chat modes and prompt files.

```
packages/<name>/
├── README.md                            # top-level: purpose, layout, links
├── claude-code/                         # installable Claude Code plugin
│   ├── .claude-plugin/plugin.json       # always (plugin manifest)
│   ├── agents/<name>.md                 # subagent (optional)
│   ├── skills/<name>/SKILL.md           # skill (optional)
│   ├── commands/<name>.md               # slash command (optional)
│   └── README.md                        # install / usage
└── github-copilot/                      # installable Copilot payload
    ├── agents/<name>.agent.md           # chat mode (optional)
    ├── prompts/<name>.prompt.md         # prompt file (optional)
    ├── install.sh                       # always (Bash deploy script)
    ├── install.ps1                      # always (PowerShell deploy script)
    └── README.md                        # install / usage
```

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
| `packages/<name>/claude-code/agents/<name>.md` | `.claude/agents/<name>.md` |
| `packages/<name>/claude-code/skills/<name>/` | `.claude/skills/<name>/` |
| `packages/<name>/claude-code/commands/<name>.md` | `.claude/commands/<name>.md` |
| `packages/<name>/github-copilot/agents/<name>.agent.md` | `.github/agents/<name>.agent.md` |
| `packages/<name>/github-copilot/prompts/<name>.prompt.md` | `.github/prompts/<name>.prompt.md` |

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

**Claude Code** — install the package as a plugin:

```
/plugin install <absolute-path>/packages/<name>/claude-code
```

**GitHub Copilot** — run the install script in your target repo:

```bash
# Linux / macOS
/path/to/maruti/packages/<name>/github-copilot/install.sh /path/to/target-repo

# Windows
powershell /path/to/maruti/packages/<name>/github-copilot/install.ps1 -Target C:\path\to\target-repo
```

You can also vendor by direct copy — copy the platform variant you need into
the consumer's expected location (e.g. `.github/agents/<name>.agent.md` or
`.claude/skills/<name>/`).

## Currently authored agents

- [`assistant-wizard/`](assistant-wizard/) — designs and generates new custom
  packages (subagent / skill / slash command / chat mode / prompt file) for
  Claude Code, GitHub Copilot, or both.
- [`mcp-tool-architect/`](mcp-tool-architect/) — turns a problem statement
  into a decision-ready MCP tool architecture and writes the durable
  spec/guardrails/success-criteria docs.
