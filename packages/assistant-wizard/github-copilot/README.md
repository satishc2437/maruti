# Assistant-Wizard — GitHub Copilot variant

Installable form of Assistant-Wizard for use in GitHub Copilot CLI as a custom agent.

## Install

From a Copilot CLI session in the target repository:

```
copilot plugin marketplace add satishc-dev/maruti
copilot plugin install assistant-wizard@maruti
```

The first command is one-time per machine; subsequent installs only need the second line.

## Manual install

If you prefer to vendor the agent directly into a repo (no plugin system):

```bash
mkdir -p .github/agents
cp agents/assistant-wizard.agent.md .github/agents/assistant-wizard.agent.md
```

Copilot CLI also reads `~/.copilot/agents/` for personal-scope agents if you want it available across all your projects.

## Usage

Once installed, switch to the **Assistant-Wizard** agent in your Copilot CLI session and describe what you want to build.

Assistant-Wizard will ask which target environment(s), capture your intent, recommend the right primitive per environment, and generate a deployable payload at `packages/<new-name>/`.

## Notes vs. the Claude Code variant

The Claude Code variant runs a build/review subagent loop (`wizard-builder` + `wizard-reviewer`) that gates the generated artifacts before declaring done. Copilot CLI's chat-mode model runs interview and generation in a single agent context — there's no automated reviewer pass, so final artifact quality depends more on the chat mode's own discipline and your review.
