# Maruti: MCP Tools Monorepo

A curated collection of self-contained Model Context Protocol (MCP) tools/servers.
Each tool lives in its own folder, is its own Python project, and can be used
independently.

## Key Principles

- **Isolation**: Tool code must not depend on other tools.
- **Self-contained**: Each tool includes its own source, tests, and documentation.
- **Devcontainer-first**: Development and testing are supported inside the repo dev container.
- **Python**: Standard runtime is Python 3.14 (each tool declares `requires-python`).
- **Quality**: TDD and >95% coverage per tool are expected.

## Repository Layout

```text
mcp-tools/
├── agent-memory/
├── onenote-reader/
├── pdf-reader/
└── xlsx-reader/
```

## Dev Container

Open this repository in the dev container to get a consistent environment.
See [.devcontainer/README.md](.devcontainer/README.md) for details.

## Run a Tool

From the repository root:

```bash
uv run pdf-reader
uv run xlsx-reader
uv run onenote-reader
uv run agent-memory
```

## Run Tests

Run all tests:

```bash
uv sync --dev --all-packages
uv run pytest
```

Run a specific tool’s tests (example):

```bash
uv run pytest mcp-tools/pdf-reader -v
```

## Docstring Checks

Run docstring lint (pydocstyle `D*` rules via `ruff`, Google convention) over the
repo’s in-scope sources:

```bash
uv run ruff check --select D mcp-tools/*/src
```

Notes:
- Scope is intentionally limited to tool source packages under `mcp-tools/*/src/**`.
- Tests are excluded by configuration.
- If a repo-root `main.py` exists, include it in the command.

## Using Tools via `uvx` (from GitHub)

Each tool’s README provides a copy/paste snippet intended for MCP client
configuration that runs the tool via `uvx` directly from GitHub.

General pattern (placeholders):

```bash
uvx --from "git+https://github.com/<owner>/<repo>.git@<ref>#subdirectory=mcp-tools/<tool-folder>" \
  python -m <tool_module>
```

Notes:
- Replace `<ref>` with a tag/commit for reproducibility.
- Use the module/entrypoint defined by the tool.

## Adding a New Tool

- Create a new folder under `mcp-tools/<tool-name>/` with its own `pyproject.toml`.
- Ensure it mentions MCP in the project metadata so devcontainer auto-discovery can install it.
- Document usage in `mcp-tools/<tool-name>/README.md`, including the `uvx` snippet.

## Governance

Project development is governed by the constitution in
[.specify/memory/constitution.md](.specify/memory/constitution.md).

## Cleanup (Review Only)

Potential repo-root removal candidates are listed in
[REMOVAL_CANDIDATES.md](REMOVAL_CANDIDATES.md).

Nothing is deleted as part of generating that report; deletions require explicit confirmation.

## Note on `uv sync` in a Workspace

This repo is a `uv` workspace (multiple independent Python projects under `mcp-tools/`).

- If you want to run the *root* test suite (which imports all tools), use:

  ```bash
  uv sync --dev --all-packages
  uv run pytest -q
  ```

- If you run `uv sync` at the repo root *without* `--all-packages`, `uv` may remove dependencies that belong to individual tools (because it is syncing the environment to just the root project). That can lead to import errors like missing `openpyxl`, `mcp`, `pypdf`, or tool packages such as `pdf_reader`.

- For per-tool work, `cd mcp-tools/<tool>` and run:

  ```bash
  uv sync --dev
  uv run pytest
  ```
