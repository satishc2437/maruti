# Agent Memory MCP — Usage Examples

Quick, deterministic examples for calling the MCP tools over JSON-RPC stdio.

- Package: [`agent_memory`](agent-memory/src/agent_memory/__init__.py:1)
- Entry: [`__main__.py`](agent-memory/src/agent_memory/__main__.py:1)
- Server: [`server.py`](agent-memory/src/agent_memory/server.py:1)
- Tools: [`tools.py`](agent-memory/src/agent_memory/tools.py:1)
- Safety: [`safety.py`](agent-memory/src/agent_memory/safety.py:1)
- Schemas: [`schemas.py`](agent-memory/src/agent_memory/schemas.py:1)
- Errors: [`errors.py`](agent-memory/src/agent_memory/errors.py:1)

## Start Server

Option A: uvx (recommended)
- Install locally into the environment (editable):
```
cd agent-memory && uv pip install -e .
```
- Start the server:
```
uvx agent-memory
```

Option B: Python module with src layout
```
cd agent-memory && PYTHONPATH=./src python -m agent_memory
```

The server reads one-line JSON requests from stdin and writes one-line JSON responses to stdout.

## 1) Start a Session

Create or open a session log for an agent in the repository root.

Request:

```
# Using uvx (after 'uv pip install -e .'):
printf '{"jsonrpc":"2.0","id":"1","method":"tool_call","params":{"name":"start_session","arguments":{"agent_name":"aristotle","repo_root":"/app"}}}\n' | uvx agent-memory

# Using python module:
printf '{"jsonrpc":"2.0","id":"1","method":"tool_call","params":{"name":"start_session","arguments":{"agent_name":"aristotle","repo_root":"/app"}}}\n' | PYTHONPATH=./src python -m agent_memory
```

Example Response:

```
{"jsonrpc":"2.0","id":"1","result":{"ok":true,"session_file":"/app/.github/agent-memory/aristotle/logs/2025-12-14.md","created":true,"schema_version":"v1","version":"1.0.0"}}
```

Repo layout created:
- `.github/agent-memory/<agent>/logs/YYYY-MM-DD.md`
- `.github/agent-memory/<agent>/_summary.md`
- `.github/agent-memory/<agent>/_schema.md`

## 2) Append an Entry

Append content under a valid section in the session log.

Allowed sections: Context, Discussion Summary, Decisions, Open Questions, Next Actions.

Request:

```
# uvx:
printf '{"jsonrpc":"2.0","id":"2","method":"tool_call","params":{"name":"append_entry","arguments":{"agent_name":"aristotle","repo_root":"/app","section":"Decisions","content":"Adopt repo-local memory with schema v1."}}}\n' | uvx agent-memory

# python module:
printf '{"jsonrpc":"2.0","id":"2","method":"tool_call","params":{"name":"append_entry","arguments":{"agent_name":"aristotle","repo_root":"/app","section":"Decisions","content":"Adopt repo-local memory with schema v1."}}}\n' | PYTHONPATH=./src python -m agent_memory
```

Response:

```
{"jsonrpc":"2.0","id":"2","result":{"ok":true,"session_file":"/app/.github/agent-memory/aristotle/logs/2025-12-14.md","section":"Decisions","appended":true,"version":"1.0.0"}}
```

## 3) Read Summary

Read the canonical `_summary.md`, initializing it if empty.

Request:

```
# uvx:
printf '{"jsonrpc":"2.0","id":"3","method":"tool_call","params":{"name":"read_summary","arguments":{"agent_name":"aristotle","repo_root":"/app"}}}\n' | uvx agent-memory

# python module:
printf '{"jsonrpc":"2.0","id":"3","method":"tool_call","params":{"name":"read_summary","arguments":{"agent_name":"aristotle","repo_root":"/app"}}}\n' | PYTHONPATH=./src python -m agent_memory
```

Response:

```
{"jsonrpc":"2.0","id":"3","result":{"ok":true,"summary":"# Agent Summary (aristotle)\n\n## Context\n\n## Discussion Summary\n\n## Decisions\n\n## Open Questions\n\n## Next Actions\n","schema_version":"v1","version":"1.0.0"}}
```

## 4) Update Summary (append or replace)

Append to a section:

```
# uvx:
printf '{"jsonrpc":"2.0","id":"4","method":"tool_call","params":{"name":"update_summary","arguments":{"agent_name":"aristotle","repo_root":"/app","section":"Decisions","content":"Use agent-memory v1 as persistence layer.","mode":"append"}}}\n' | uvx agent-memory

# python module:
printf '{"jsonrpc":"2.0","id":"4","method":"tool_call","params":{"name":"update_summary","arguments":{"agent_name":"aristotle","repo_root":"/app","section":"Decisions","content":"Use agent-memory v1 as persistence layer.","mode":"append"}}}\n' | PYTHONPATH=./src python -m agent_memory
```

Replace a section:

```
# uvx:
printf '{"jsonrpc":"2.0","id":"5","method":"tool_call","params":{"name":"update_summary","arguments":{"agent_name":"aristotle","repo_root":"/app","section":"Context","content":"Project=Memory MCP; Focus=Schema; Stage=Implementation","mode":"replace"}}}\n' | uvx agent-memory

# python module:
printf '{"jsonrpc":"2.0","id":"5","method":"tool_call","params":{"name":"update_summary","arguments":{"agent_name":"aristotle","repo_root":"/app","section":"Context","content":"Project=Memory MCP; Focus=Schema; Stage=Implementation","mode":"replace"}}}\n' | PYTHONPATH=./src python -m agent_memory
```

Responses:

```
{"jsonrpc":"2.0","id":"4","result":{"ok":true,"updated":true,"section":"Decisions","mode":"append","version":"1.0.0"}}
{"jsonrpc":"2.0","id":"5","result":{"ok":true,"updated":true,"section":"Context","mode":"replace","version":"1.0.0"}}
```

## 5) List Sessions

List `YYYY-MM-DD.md` files newest → oldest, with optional limit.

Request:

```
# uvx:
printf '{"jsonrpc":"2.0","id":"6","method":"tool_call","params":{"name":"list_sessions","arguments":{"agent_name":"aristotle","repo_root":"/app","limit":10}}}\n' | uvx agent-memory

# python module:
printf '{"jsonrpc":"2.0","id":"6","method":"tool_call","params":{"name":"list_sessions","arguments":{"agent_name":"aristotle","repo_root":"/app","limit":10}}}\n' | PYTHONPATH=./src python -m agent_memory
```

Response:

```
{"jsonrpc":"2.0","id":"6","result":{"ok":true,"sessions":["2025-12-14.md"]}}
```

## Error Examples

Invalid section:

Request:

```
# uvx:
printf '{"jsonrpc":"2.0","id":"7","method":"tool_call","params":{"name":"append_entry","arguments":{"agent_name":"aristotle","repo_root":"/app","section":"Thoughts","content":"Should be rejected."}}}\n' | uvx agent-memory

# python module:
printf '{"jsonrpc":"2.0","id":"7","method":"tool_call","params":{"name":"append_entry","arguments":{"agent_name":"aristotle","repo_root":"/app","section":"Thoughts","content":"Should be rejected."}}}\n' | PYTHONPATH=./src python -m agent_memory
```

Response:

```
{"jsonrpc":"2.0","id":"7","result":{"ok":false,"error":"InvalidSection","message":"Section 'Thoughts' is not defined in schema"}}
```

Malformed JSON:

Send a broken line:

```
printf '{"jsonrpc": "2.0", "id": 8, "method": "tool_call", \n' | PYTHONPATH=./src python -m agent_memory
```

Response:

```
{"jsonrpc":"2.0","id":null,"error":{"ok":false,"code":"UserInput","message":"Malformed JSON"}}
```

## MCP Client Configuration (mcp.json)

Register agent_memory as an MCP server for compatible clients (e.g., VS Code MCP-aware plugins).

Example `mcp.json`:

```json
{
  "version": "1.0",
  "servers": {
    "agent-memory": {
      "command": "uvx",
      "args": ["agent-memory"],
      "env": {
        // Optional: set default repo_root for tools; clients may pass dynamically
        "AGENT_MEMORY_DEFAULT_REPO_ROOT": "/app"
      },
      "transport": "stdio",
      "autoStart": true
    }
  }
}
```

Notes:
- Ensure agent-memory is installed locally: `cd agent-memory && uv pip install -e .`
- Transport is stdio; clients send JSON-RPC one-line messages.
- If your client supports per-server arguments, you can set working directory or env as needed.

## Tips

- Always set `repo_root` to the repository base you want to persist memory within.
- No deletes; operations are append/replace only per tool contract.
- For uvx-based run without PYTHONPATH, install locally:
  - `cd agent-memory && uv pip install -e .`
  - Then: `uvx agent-memory`

See also:
- README: [`agent-memory/README.md`](agent-memory/README.md)
- Tests: [`agent-memory/test_server.py`](agent-memory/test_server.py:1)
