# maruti

Monorepo for a growing collection of focused Model Context Protocol (MCP) servers.

## Philosophy
- Each server lives in its own directory with an isolated `pyproject.toml`
- Strong safety constraints (no unintended network / writes)
- Clear separation: core logic vs MCP adapter layer
- Minimal duplication: detailed usage lives inside each server’s own README

## Available Servers
| Server | Description | Status | Docs |
|--------|-------------|--------|------|
| pdf-reader | PDF text / metadata / tables / (streaming) extraction | Stable v1.0.0 | See `pdf-reader/README.md` and `pdf-reader/MCP_USAGE.md` |
| xlsx-reader | Excel (.xlsx) workbook reading and comprehensive editing | Beta v1.0.0 | See `xlsx-reader/README.md` and `xlsx-reader/USAGE_EXAMPLES.md` |

## Getting Started (General Pattern)
```bash
cd <server-dir>
uv pip install -e .        # editable dev install (preferred)
# or ephemeral: uvx --from . python -m <package> --test
```
Then configure your MCP client (Claude Desktop / VS Code) pointing `cwd` to the server directory.

## Adding a New Server
1. Create directory `<new-server>/`
2. Add `pyproject.toml` + `src/<package_name>/`
3. Provide `__main__.py` with optional `--test`
4. Implement tools with validation + error taxonomy
5. Add a concise `README.md` (details stay local)

## Error Taxonomy (shared convention)
`UserInput | Forbidden | NotFound | Timeout | Internal | Cancelled`

## Roadmap (Planned)
- text-indexer
- image-metadata
- git-inspector
- metrics-hub

PRs / issues with proposals welcome.

## License
MIT (see `LICENSE`).

For full PDF reader instructions, do not duplicate here—refer directly to:
- `pdf-reader/README.md`
- `pdf-reader/MCP_USAGE.md`

End.
