# Maruti

A plugin marketplace for **Claude Code** and **GitHub Copilot CLI** — plus the MCP tools the plugins are built around.

Maruti ships:

- **Five installable agent packages** — coordinated subagents, skills, slash commands, chat modes, and prompt files for both Claude Code and Copilot CLI.
- **Three MCP tools** — self-contained Python MCP servers distributed via `uvx`.

## Plugin marketplace

Maruti is registered as a marketplace for both supported platforms:

| Platform | Marketplace manifest | Add to client |
|---|---|---|
| Claude Code | [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) | `/plugin marketplace add satishc-dev/maruti` |
| GitHub Copilot CLI | [`.github/plugin/marketplace.json`](.github/plugin/marketplace.json) | `copilot plugin marketplace add satishc-dev/maruti` |

Once the marketplace is added, install any plugin by name:

```
# Claude Code
/plugin install <plugin-name>@maruti

# Copilot CLI (works as a shell command or, inside an interactive session, as a slash command)
copilot plugin install <plugin-name>@maruti
/plugin install <plugin-name>@maruti
```

The marketplace-add line is one-time per machine; subsequent installs only need the install line.

### Managing installed plugins (Copilot CLI)

```
copilot plugin list                               # list installed plugins
copilot plugin update <plugin-name>               # update to the latest version
copilot plugin uninstall <plugin-name>            # remove a plugin
copilot plugin marketplace list                   # list added marketplaces
copilot plugin marketplace browse maruti          # browse plugins in this marketplace
copilot plugin marketplace remove maruti          # remove this marketplace (add --force if plugins are installed)
```

### Available plugins

| Plugin | Purpose | Claude Code | Copilot CLI |
|---|---|:-:|:-:|
| [`pm-team`](packages/pm-team/) | Multi-agent PM team: intent → specs → spec PR → Kanban WIs | ✓ | ✓ |
| [`dev-team`](packages/dev-team/) | Multi-agent dev team: WI → design → parallel impl → review → PR | ✓ | ✓ |
| [`assistant-wizard`](packages/assistant-wizard/) | Designs and generates new custom agents/skills/commands for either platform | ✓ | ✓ |
| [`mcp-tool-architect`](packages/mcp-tool-architect/) | Turns a problem statement into a decision-ready MCP tool architecture | ✓ | ✓ |
| [`marketing-guru`](packages/marketing-guru/) | Proactive MBA-grade marketing advisor for a bike-company simulation | ✓ | ✓ |

Each package's own README documents its install variants, layout, and any platform-specific differences.

## MCP tools

Three MCP servers, each independently installable via `uvx` straight from GitHub:

```text
mcp-tools/
├── agent-memory/    # persistent file-based memory for agents
├── pdf-reader/      # MCP server that reads PDFs
└── xlsx-reader/     # MCP server that reads Excel files
```

General install snippet for an MCP client:

```bash
uvx --from "git+https://github.com/satishc-dev/maruti.git@<ref>#subdirectory=mcp-tools/<tool-folder>" \
  python -m <tool_module>
```

Each tool's README has the exact snippet to drop into your MCP client config. Replace `<ref>` with a tag or commit for reproducibility.

## Repository layout

```text
maruti/
├── .claude-plugin/marketplace.json   # Claude Code marketplace
├── .github/plugin/marketplace.json   # Copilot CLI marketplace
├── packages/                         # plugin packages (one folder per plugin)
│   ├── pm-team/{claude-code,github-copilot}/
│   ├── dev-team/{claude-code,github-copilot}/
│   ├── assistant-wizard/{claude-code,github-copilot}/
│   ├── mcp-tool-architect/{claude-code,github-copilot}/
│   └── marketing-guru/{claude-code,github-copilot}/
├── mcp-tools/                        # MCP servers (one folder per tool)
│   ├── agent-memory/
│   ├── pdf-reader/
│   └── xlsx-reader/
├── .claude/                          # symlink mirror of packages/*/claude-code/
├── .github/agents/, .github/skills/  # symlink mirror of packages/*/github-copilot/
├── docs/                             # Constitution + spec template
├── scripts/                          # link_packages.py (manages mirrors)
└── .devcontainer/                    # canonical dev environment
```

The `.claude/` and `.github/agents|skills|prompts/` mirrors are **managed** by [`scripts/link_packages.py`](scripts/README.md) and enforced by CI — never edit those directly; edit the source under `packages/<name>/`.

## Working in this repo

### Dev container

Open this repository in the dev container to get a consistent environment (Python 3.14, `uv`, MCP tools installed editable). See [`.devcontainer/README.md`](.devcontainer/README.md).

### Running MCP tools locally

```bash
uv run pdf-reader
uv run xlsx-reader
uv run agent-memory
```

### Tests

```bash
# Full workspace (recommended for root-level testing)
uv sync --dev --all-packages
uv run pytest

# Single tool
uv run pytest mcp-tools/pdf-reader -v

# Per-tool work (faster iteration)
cd mcp-tools/<tool> && uv sync --dev && uv run pytest
```

> If you run `uv sync` at the repo root *without* `--all-packages`, `uv` may remove dependencies that belong to individual tools. Always pass `--all-packages` when you need the full test env.

### Quality gates (CI-relevant)

```bash
# Docstring lint (scope limited to mcp-tools/*/src by config)
uv run ruff check --select D mcp-tools/*/src

# Pylint — must exit 0 (zero E/W/F messages)
uv run pylint mcp-tools/*/src

# Coverage gate — >95% per tool (enforced via --cov-fail-under=95)
cd mcp-tools/<tool> && uv run pytest --cov --cov-fail-under=95
```

## Authoring a new plugin

The recommended path is to use the [`assistant-wizard`](packages/assistant-wizard/) plugin itself: it asks for the target environment(s), captures your intent, recommends the right primitive per environment, and emits the package layout — Claude Code, Copilot CLI, or both.

For the by-hand path, see [`packages/README.md`](packages/README.md).

## Adding a new MCP tool

1. Create `mcp-tools/<name>/` with its own `pyproject.toml` declaring `requires-python = ">=3.14"` and mentioning `mcp` (devcontainer auto-discovery keys on the literal string "mcp" in the project file).
2. Add the path to `[tool.uv.workspace].members` in the root `pyproject.toml`.
3. Layout: `src/<pkg>/{__init__.py, __main__.py, server.py}` plus `tests/`.
4. Declare a `[project.scripts]` entry so `uv run <tool>` works.
5. Write a README with a copy/pasteable `uvx` snippet targeting `github.com/satishc-dev/maruti`.
6. Rebuild the devcontainer (or run `.devcontainer/post-create.sh`) so auto-discovery installs it editable.

## Governance

Project development is governed by the constitution in [`docs/Constitution.md`](docs/Constitution.md). When constitutional rules and this README disagree, the constitution wins.
