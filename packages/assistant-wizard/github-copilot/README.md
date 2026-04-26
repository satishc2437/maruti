# Assistant-Wizard — GitHub Copilot variant

Installable form of Assistant-Wizard for use in GitHub Copilot Chat.

## Install

Run the install script from this directory, passing the path to the consuming repository (defaults to the current directory):

```bash
# Linux / macOS
./install.sh /path/to/target-repo

# Windows (PowerShell)
.\install.ps1 -Target C:\path\to\target-repo
```

The script copies the chat mode into `<target>/.github/agents/`. In VS Code with Copilot Chat, the agent then appears in the chat-mode picker as **Assistant-Wizard**.

## Usage

1. Open Copilot Chat.
2. Switch the chat mode to **Assistant-Wizard**.
3. Describe what you want to build.

Assistant-Wizard will then ask which target environment(s), capture your intent, recommend the right primitive per environment, and generate a deployable payload at `packages/<new-name>/`.

## Manual install

If you'd rather not run the script, copy the file directly:

```bash
mkdir -p <target>/.github/agents
cp agents/<name>.agent.md <target>/.github/agents/
```
