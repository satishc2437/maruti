# Assistant-Wizard

A guided creation flow that designs and generates new custom packages — subagents, skills, slash commands, chat modes, prompt files — for **Claude Code**, **GitHub Copilot**, or both.

## What it does

When invoked, Assistant-Wizard asks which target environment(s), captures your intent, **recommends the right primitive per environment with rationale**, and emits a deployable payload at `packages/<new-name>/`.

It picks the right primitive for the job rather than defaulting to "an agent". Examples:

- **Interactive interview-driven workflow** → Skill (Claude Code) + Chat mode (Copilot)
- **Single-shot research / analysis task** → Subagent (Claude Code) + Chat mode (Copilot)
- **Reusable prompt template / shortcut** → Slash command (Claude Code) + Prompt file (Copilot)

## Install

**Claude Code** — from a Claude Code session in the target repo:

```
/plugin marketplace add satishc-dev/maruti
/plugin install assistant-wizard@maruti
```

**GitHub Copilot CLI** — from a Copilot CLI session in the target repo:

```
copilot plugin marketplace add satishc-dev/maruti
copilot plugin install assistant-wizard@maruti
```

For each platform, the marketplace-add line is one-time per machine; subsequent installs only need the install line. For local-checkout and project-local-copy alternatives, see [`claude-code/README.md`](claude-code/README.md#install) and [`github-copilot/README.md`](github-copilot/README.md).

## Roles

Assistant-Wizard is a coordinated team — a skill that interviews the user and two subagents that produce and gate the output:

- **`assistant-wizard`** (skill) — orchestrator + intent interview. Loaded into the main agent's context (multi-turn interview is natural there). Synthesizes a structured **design brief** after the interview, then drives the build/review loop.
- **`wizard-builder`** (subagent) — receives the design brief in a cold context and writes every file in the brief's output-paths list. Runs a mandatory self-check against the rubric before reporting.
- **`wizard-reviewer`** (subagent) — read-only gate. Reads only the design brief and the on-disk artifacts (no interview transcript), scores against a 7-point prompt-engineering rubric plus task-specific criteria, returns structured **go/no-go** with line-anchored, actionable feedback.

The skill auto-iterates builder ↔ reviewer up to **3 iterations** on `no-go`, then escalates to the user with the reviewer's outstanding feedback.

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
│   ├── agents/
│   │   ├── wizard-builder.md
│   │   └── wizard-reviewer.md
│   └── README.md
└── github-copilot/        # installable Copilot CLI plugin
    ├── agents/
    │   └── assistant-wizard.agent.md
    └── README.md
```

The `claude-code/` and `github-copilot/` subdirectories are **independently installable**. See their READMEs for install steps.

> The build/review loop (`wizard-builder` + `wizard-reviewer`) is a Claude Code-only feature. The GitHub Copilot variant runs interview and generation in a single chat-mode context — there's no automated reviewer pass, so for Copilot users the final artifact quality depends more on the chat mode's own discipline and the user's review.

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
    ├── skills/<new-name>/SKILL.md        # if skill
    ├── prompts/<new-name>.prompt.md      # if prompt file
    └── README.md
```

## Workflow

```
/assistant-wizard
  └─► main agent (with assistant-wizard skill loaded)
        ├── ask which target environment(s)
        ├── capture intent (2-3 sentences)
        ├── recommend primitive per environment (with rationale; user override allowed)
        ├── 3-5 question interview tuned to chosen primitive(s)
        ├── summarize and confirm
        ├── synthesize design brief (single source of truth for the loop)
        └── build/review loop (≤3 iterations):
              ├─► wizard-builder (writes every file in brief's output-paths list)
              │       └── self-check against rubric → report
              ├─► wizard-reviewer (cold context, read-only)
              │       └── 7-point rubric + task-specific criteria → go / no-go
              ├── on no-go: dispatch revision to builder with reviewer's Required actions
              └── on go (or iteration 3 exhausted): report to user
```
