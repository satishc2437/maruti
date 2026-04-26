# Assistant-Wizard

A guided creation flow that designs and generates new custom packages — subagents, skills, slash commands, chat modes, prompt files — for **Claude Code**, **GitHub Copilot**, or both.

## What it does

When invoked, Assistant-Wizard asks which target environment(s), captures your intent, **recommends the right primitive per environment with rationale**, and emits a deployable payload at `packages/<new-name>/`.

It picks the right primitive for the job rather than defaulting to "an agent". Examples:

- **Interactive interview-driven workflow** → Skill (Claude Code) + Chat mode (Copilot)
- **Single-shot research / analysis task** → Subagent (Claude Code) + Chat mode (Copilot)
- **Reusable prompt template / shortcut** → Slash command (Claude Code) + Prompt file (Copilot)

## Layout of this package

```
packages/assistant-wizard/
├── README.md              # this file
├── claude-code/           # installable Claude Code plugin
│   ├── .claude-plugin/
│   │   └── plugin.json
│   ├── skills/
│   │   └── assistant-wizard/
│   │       └── SKILL.md
│   └── README.md
└── github-copilot/        # installable Copilot payload
    ├── packages/
    │   └── assistant-wizard.agent.md
    ├── install.sh
    ├── install.ps1
    └── README.md
```

The `claude-code/` and `github-copilot/` subdirectories are **independently installable**. See their READMEs for install steps.

## Output contract for generated packages

Generated packages follow the same shape, with primitives included only when the user picked them:

```
packages/<new-name>/
├── README.md
├── claude-code/                          # only if target includes claude-code
│   ├── .claude-plugin/plugin.json
│   ├── agents/<new-name>.md              # if subagent
│   ├── skills/<new-name>/SKILL.md        # if skill
│   ├── commands/<new-name>.md            # if slash command
│   └── README.md
└── github-copilot/                       # only if target includes github-copilot
    ├── agents/<new-name>.agent.md        # if chat mode
    ├── prompts/<new-name>.prompt.md      # if prompt file
    ├── install.sh
    ├── install.ps1
    └── README.md
```

## Workflow

1. Invoke Assistant-Wizard.
2. It asks **which target environment(s)**: Claude Code, GitHub Copilot, or both.
3. It asks you to **describe your intent** (2–3 sentences).
4. It **recommends a primitive per environment** with rationale, and lets you override.
5. It runs a 3–5 question interview tuned to the chosen primitive(s).
6. It summarizes the design and asks for confirmation.
7. It writes the new package under `packages/<new-name>/`.
