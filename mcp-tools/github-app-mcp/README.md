# github-app-mcp

A Model Context Protocol (MCP) server that lets agents perform a strictly allow-listed set of GitHub operations using **only a GitHub App identity**.

This tool is designed to be:
- Server-owned auth (App JWT → installation token)
- Policy guarded (repo allowlist, PR-only workflow, protected branches)
- Audited (JSONL audit events with correlation IDs)
- Secret-safe (never returns tokens, key material, or installation IDs)

## Safety (high level)

- No personal credentials/PATs are accepted.
- No arbitrary GitHub API passthrough is supported.
- Network egress is restricted to `https://api.github.com`.

## Supported tools (allow-listed)

The server exposes a fixed, allow-listed set of operations:

- `get_repository`
- `list_branches`
- `get_file`
- `list_pull_requests`
- `list_issues`
- `create_branch`
- `commit_changes`
- `open_pull_request`
- `comment_on_issue`

Every tool response includes a `correlation_id` which can be used to find the matching audit log entries.

## Resources

- `github-app-mcp://server-status`: non-secret server configuration and limits
- `github-app-mcp://capabilities`: allow-listed operations and safety constraints

## Run (development)

From this tool folder:

```bash
uv sync --dev
uv run python -m github_app_mcp --test
```

To run the full test suite (including the tool-local coverage gate):

```bash
uv run pytest -q
```

## Run via uvx (from GitHub)

This is the recommended distribution format for MCP clients.

```bash
uvx --from "git+https://github.com/<owner>/<repo>.git@<ref>#subdirectory=mcp-tools/github-app-mcp" \
  python -m github_app_mcp
```

## Configuration

This server is configured via host-provided environment variables (agents must not supply secrets):

| Variable | Required | Meaning |
|---|---:|---|
| `GITHUB_APP_ID` | yes | GitHub App ID |
| `GITHUB_APP_INSTALLATION_ID` | yes | Installation ID for the app |
| `GITHUB_APP_PRIVATE_KEY_PATH` | yes | Filesystem path to the app private key `.pem` |
| `GITHUB_APP_MCP_ALLOWED_REPOS` | no | Comma-separated `owner/repo` allowlist. If set, requests outside this list are denied. |
| `GITHUB_APP_MCP_PR_ONLY` | no | `1`/`0`. If enabled, denies write operations that bypass the PR workflow. |
| `GITHUB_APP_MCP_PROTECTED_BRANCHES` | no | Comma-separated branch name/pattern list treated as protected. |
| `GITHUB_APP_MCP_AUDIT_LOG_PATH` | no | Optional file sink for JSONL audit events. If unset, auditing still occurs (stderr/logging). |

## Example MCP client config

Example `mcp.json` snippet (adjust for your MCP client as needed):

```json
{
  "servers": {
    "github-app-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/<owner>/<repo>.git@<ref>#subdirectory=mcp-tools/github-app-mcp",
        "python",
        "-m",
        "github_app_mcp"
      ],
      "env": {
        "GITHUB_APP_ID": "<app-id>",
        "GITHUB_APP_INSTALLATION_ID": "<installation-id>",
        "GITHUB_APP_PRIVATE_KEY_PATH": "/absolute/path/to/private-key.pem",
        "GITHUB_APP_MCP_ALLOWED_REPOS": "octo-org/example-repo",
        "GITHUB_APP_MCP_PR_ONLY": "1",
        "GITHUB_APP_MCP_PROTECTED_BRANCHES": "main,master",
        "GITHUB_APP_MCP_AUDIT_LOG_PATH": "/absolute/path/to/github-app-mcp.audit.jsonl"
      }
    }
  }
}
```

## Self-test mode

Run a lightweight, local self-test (no GitHub API calls) that validates the server can build tool/resource metadata:

```bash
uv run python -m github_app_mcp --test
```

Exit code is `0` on success. If it fails, it emits a safe error message and exits non-zero.
