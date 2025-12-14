# Agent Memory MCP

Deterministic, schema-enforced, repo-local memory tools for AI agents. Implements a Memory Control Plane that persists session logs and curated summaries inside the consuming Git repository.

- Package: [`agent_memory`](src/agent_memory/__init__.py)
- Entry: [`__main__.py`](src/agent_memory/__main__.py:1)
- Server: [`server.py`](src/agent_memory/server.py:1)
- Tools: [`tools.py`](src/agent_memory/tools.py:1)
- Safety: [`safety.py`](src/agent_memory/safety.py:1)
- Schemas: [`schemas.py`](src/agent_memory/schemas.py:1)
- Errors: [`errors.py`](src/agent_memory/errors.py:1)
- Project: [`pyproject.toml`](pyproject.toml)

## Design Principles

- Deterministic: no probabilistic behavior, no implicit writes.
- Schema-enforced: invalid writes rejected.
- Repo-local: memory lives under `.github/agent-memory/<agent>/`.
- Agent-safe: read freely; write only via explicit tool calls.
- Human-controlled: tool persists; humans curate durable knowledge.

## Repository Contract

Required layout (auto-created if missing):

```
.github/
└─ agent-memory/
   └─ <agent-name>/
      ├─ logs/
      │  └─ YYYY-MM-DD.md
      ├─ _summary.md
      └─ _schema.md
```

## Safety

- Filesystem confined to provided repo_root.
- Path traversal guarded; writes are deterministic; no deletes.
- No network calls; no subprocess execution.

## Run

- Recommended in VS Code terminal:

```
cd agent-memory && PYTHONPATH=./src python -m agent_memory
```

This starts a JSON-RPC stdio server. Send one-line JSON requests via stdin.

## Tools

- start_session: create/open session log for date.
- append_entry: append content under a valid section.
- read_summary: read or initialize `_summary.md`.
- update_summary: append/replace a section in `_summary.md`.
- list_sessions: list `YYYY-MM-DD.md` newest → oldest.

Valid sections (schema v1): Context, Discussion Summary, Decisions, Open Questions, Next Actions.

## Usage Examples

Send requests via pipe using shell printf.

- start_session

```
printf '{"jsonrpc":"2.0","id":"1","method":"tool_call","params":{"name":"start_session","arguments":{"agent_name":"aristotle","repo_root":"/app"}}}\n' | PYTHONPATH=./src python -m agent_memory
```

- append_entry

```
printf '{"jsonrpc":"2.0","id":"2","method":"tool_call","params":{"name":"append_entry","arguments":{"agent_name":"aristotle","repo_root":"/app","section":"Decisions","content":"Adopt repo-local memory with schema v1."}}}\n' | PYTHONPATH=./src python -m agent_memory
```

- read_summary

```
printf '{"jsonrpc":"2.0","id":"3","method":"tool_call","params":{"name":"read_summary","arguments":{"agent_name":"aristotle","repo_root":"/app"}}}\n' | PYTHONPATH=./src python -m agent_memory
```

- update_summary (append)

```
printf '{"jsonrpc":"2.0","id":"4","method":"tool_call","params":{"name":"update_summary","arguments":{"agent_name":"aristotle","repo_root":"/app","section":"Decisions","content":"Use agent-memory v1 as persistence layer.","mode":"append"}}}\n' | PYTHONPATH=./src python -m agent_memory
```

- update_summary (replace)

```
printf '{"jsonrpc":"2.0","id":"5","method":"tool_call","params":{"name":"update_summary","arguments":{"agent_name":"aristotle","repo_root":"/app","section":"Context","content":"Project=Memory MCP; Focus=Schema; Stage=Implementation","mode":"replace"}}}\n' | PYTHONPATH=./src python -m agent_memory
```

- list_sessions

```
printf '{"jsonrpc":"2.0","id":"6","method":"tool_call","params":{"name":"list_sessions","arguments":{"agent_name":"aristotle","repo_root":"/app","limit":10}}}\n' | PYTHONPATH=./src python -m agent_memory
```

## Error Shape

Errors are explicit and non-destructive:

```
{"ok": false, "error": "InvalidSection", "message": "Section 'Thoughts' is not defined in schema"}
```

Codes: UserInput, Forbidden, NotFound, Timeout, Internal, InvalidSection.

## Versioning

- Tool version: 1.0.0
- Schema version: v1 (declared in [`_schema.md`](src/agent_memory/schemas.py:1) template).
- Mismatches should emit warnings; backward compatibility preferred.

## Notes

- To run via uvx without PYTHONPATH, install the package locally:
  - `cd agent-memory && uv pip install -e .`
  - Then `uvx python -m agent_memory`.
