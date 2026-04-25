# {{TOOL_HYPHEN}}

{{TOOL_DESCRIPTION}}

## Run

```bash
# Local (workspace dev)
uv run {{TOOL_HYPHEN}}

# Via uvx, directly from GitHub (replace <ref> with a tag/commit)
uvx --from "git+https://github.com/satishc2437/maruti.git@<ref>#subdirectory=mcp-tools/{{TOOL_HYPHEN}}" \
  python -m {{TOOL_MODULE}}
```

## MCP client configuration

```json
{
  "{{TOOL_HYPHEN}}": {
    "command": "uvx",
    "args": [
      "--from",
      "git+https://github.com/satishc2437/maruti.git@main#subdirectory=mcp-tools/{{TOOL_HYPHEN}}",
      "python",
      "-m",
      "{{TOOL_MODULE}}"
    ]
  }
}
```

## Tools exposed

(Edit this section as you implement tools.)

- `example_tool` — placeholder; replace with real tool definitions in
  `src/{{TOOL_MODULE}}/tools.py`.

## Tests

```bash
cd mcp-tools/{{TOOL_HYPHEN}} && uv run pytest
```

The 95% coverage gate is enforced via `--cov-fail-under=95` in
`pyproject.toml`. See `docs/Constitution.md §6` for the policy.

## Specs

Add spec docs under `specs/` (numbered `001-*.md`, `002-*.md`). Use
[`docs/specs-template.md`](../../docs/specs-template.md) as the
starting structure.
