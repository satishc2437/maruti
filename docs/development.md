# Development guide

How to work on Maruti — running tools, writing tests, and adding new MCP
servers. Governance and quality gates live in [`Constitution.md`](./Constitution.md);
this file is the practical companion.

## Workspace shape

Maruti is a `uv` workspace. Each MCP tool under `mcp-tools/<tool>/` is its
own independently releasable Python project with its own `pyproject.toml`,
`src/`, `tests/`, `specs/`, and `README.md`. Tools MUST NOT import each
other (see Constitution §1).

Workspace members are declared in the root `pyproject.toml` under
`[tool.uv.workspace]`.

## Commands

Run from the repo root unless noted.

```bash
# Full workspace sync — always use --all-packages at the root.
# (Without --all-packages, uv removes per-tool deps while syncing
# the root project, causing import errors across the workspace.)
uv sync --dev --all-packages

# Start a specific tool
uv run agent-memory
uv run pdf-reader
uv run xlsx-reader

# Tests — all workspace packages
uv run pytest

# Tests — single tool
uv run pytest mcp-tools/pdf-reader -v

# Tests — single test node
uv run pytest mcp-tools/pdf-reader/tests/test_pdf_tools_and_processor.py::test_pdf_processor_and_tool_endpoints -v

# Per-tool work (fastest iteration; uses the tool's local dev deps)
cd mcp-tools/<tool> && uv sync --dev && uv run pytest
```

## Quality gates

All three gates are CI-enforced and must pass before merge.

```bash
# Docstring lint (Google convention, ruff pydocstyle D* rules).
# Scope is intentionally limited to mcp-tools/*/src — tests are excluded.
uv run ruff check --select D mcp-tools/*/src

# Pylint — MUST exit 0 (zero E/W/F messages).
# Uses root .pylintrc which disables C (convention) and R (refactor) gates.
uv run pylint mcp-tools/*/src

# Coverage gate — ≥95% honest, per tool, no omit shortcuts.
cd mcp-tools/<tool> && uv run pytest --cov --cov-fail-under=95
```

## Devcontainer auto-discovery

The devcontainer's `post-create.sh` and `Dockerfile` auto-install any directory
under `mcp-tools/*/` whose `pyproject.toml` mentions the literal string `mcp`.
This is what makes new tools "just work" after a container rebuild.

Files that drive this:

- `.devcontainer/Dockerfile` — build-time pyproject.toml copy + editable install
- `.devcontainer/post-create.sh` — runtime install + convenience aliases
- `.devcontainer/add-mcp-server.sh` — helper for manual registration if needed

## Adding a new MCP tool

Use the script — it handles the steps below in one shot:

```bash
python scripts/new_mcp_tool.py <name> --description "<one-line summary>"
uv sync --dev --all-packages
cd mcp-tools/<name> && uv run pytest    # template tests pass; coverage gate is on
```

The script copies [`templates/mcp-tool/`](../templates/mcp-tool/) into
`mcp-tools/<name>/`, substitutes the four placeholders (tool hyphen
name, snake-case module, Title Case display, description), renames the
`src/__module__/` directory to match, and registers the new tool under
`[tool.uv.workspace].members` in the root `pyproject.toml`.

The instantiated tool starts with:

- An MCP `Server` skeleton in `src/<module>/server.py` with one
  `example_tool` to delete or rename.
- A `__main__.py` with the standard `parse_args` / `main` / dispatch
  shape used by the existing tools.
- `tests/test_server_handlers.py` covering `list_tools`, the example
  tool, and the unknown-name error envelope. Add tests as you replace
  the example tool with real ones; the 95% coverage gate is on.
- `specs/README.md` pointing at the canonical
  [spec template](./specs-template.md).
- A `README.md` with a working `uvx` snippet for the consumer.

Rebuild the devcontainer (or re-run `.devcontainer/post-create.sh`) if
you want auto-discovery to pick up the new tool inside the container.

### Manual fallback (no script)

If you prefer to scaffold by hand: copy `templates/mcp-tool/` into
`mcp-tools/<name>/`, rename `src/__module__/` to `src/<snake_name>/`,
search-and-replace the four `{{...}}` placeholders, and add the path to
`[tool.uv.workspace].members`. Same outcome, more typing.

## Agent markdowns

Authoring happens in `agents/<name>/`; each agent owns its `.agent.md` and
optional `<name>-internals/` directory. The `.github/agents/` tree is a
symlink mirror for this repo's own Copilot use — do not edit those symlinks;
edit the source under `agents/` instead.

The mirror is managed by `scripts/link_agents.py`:

```bash
python scripts/link_agents.py check    # report drift; CI runs this on every PR
python scripts/link_agents.py sync     # create/repair the .github/agents/ symlinks
python scripts/link_agents.py repair   # post-clone fix for Windows fallbacks
```

After authoring a new agent under `agents/<new>/`, run `sync` once and
commit the resulting symlinks.

### Windows: enable symlinks once per machine

The mirror relies on real filesystem symlinks. On Windows that needs
two one-time settings:

1. **Developer Mode** — Settings → Privacy & security → For developers →
   *Developer Mode*. This grants non-admin processes the
   `SeCreateSymbolicLinkPrivilege` that `os.symlink()` needs.
2. **Git symlink support** —
   ```
   git config --global core.symlinks true
   ```
   so symlinks come through `git clone` / `git checkout` intact rather
   than being materialized as text files containing the target path.

If you cloned the repo on Windows *before* setting `core.symlinks=true`,
the `.github/agents/` entries will be real text files containing path
strings. `python scripts/link_agents.py repair` detects this case and
converts them back into real symlinks (you'll still need Developer Mode
enabled at that point).

On Linux, macOS, and CI (Ubuntu) symlinks just work — no setup.

## Troubleshooting

**New tool not detected after devcontainer rebuild.**
Confirm the tool's `pyproject.toml` contains the literal string `mcp`. Then
run `.devcontainer/post-create.sh` manually or rebuild without cache.

**`ModuleNotFoundError` after `uv sync` at the root.**
You probably ran `uv sync` without `--all-packages`. That prunes per-tool
deps. Always sync the workspace with `uv sync --dev --all-packages`.

**Pylint gate fails locally but passes elsewhere.**
Ensure the root `.pylintrc` is being used. Run from repo root, not from
inside a tool directory.
