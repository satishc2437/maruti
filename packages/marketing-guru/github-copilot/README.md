# Marketing-Guru — GitHub Copilot variant

Installable form of Marketing-Guru for use in GitHub Copilot CLI as a skill.

## Install

From a Copilot CLI session in the target repository:

```
copilot plugin marketplace add satishc-dev/maruti
copilot plugin install marketing-guru@maruti
```

The first command is one-time per machine; subsequent installs only need the second line.

## Manual install

If you prefer to vendor the skill directly into a repo (no plugin system):

```bash
mkdir -p .github/skills/marketing-guru
cp skills/marketing-guru/SKILL.md .github/skills/marketing-guru/SKILL.md
```

Copilot CLI also reads `~/.copilot/skills/` for personal-scope skills if you want it available across all your projects.

## Usage

Once installed, Marketing-Guru activates proactively the moment the conversation touches marketing strategy, business performance, competitive positioning, segmentation/targeting/positioning, pricing, channels, promotion, brand, or anything inside an MBA bike-company simulation. No explicit invocation needed.

If you want to trigger it explicitly, mention "marketing", paste a simulation file/screenshot, or ask for a round-decision recommendation and it will engage.
