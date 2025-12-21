# Agent Memory MCP Server

A deterministic **Memory Control Plane** (MCP) server for AI agents that provides a structured, versioned, repository-backed memory system. This server enables persistent agent context across sessions with deterministic writes/reads, schema enforcement, and reuse across multiple repositories and projects.

## Features

### Core Capabilities
- **Persistent Agent Memory**: Maintain context across sessions in Git repositories
- **Structured Storage**: Schema-enforced memory with predefined sections
- **Session Management**: Create and manage daily session logs
- **Summary Management**: Persistent agent summaries with selective updates
- **Repository Integration**: Memory stored within `.github/agent-memory/` in each repository

### Design Principles
- **Deterministic**: No probabilistic behavior, no implicit writes, no auto-summarization
- **Schema-Enforced**: All memory follows a declared structure, invalid writes rejected
- **Repo-Local Storage**: Memory lives inside the consuming Git repository
- **Agent-Safe**: Agents read memory freely, write only via explicit tool calls
- **Human-Controlled**: Tool persists memory, humans decide what becomes durable

## Installation

### Prerequisites
```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies using uv
uv sync

# Or install core dependencies from PyPI
uv add mcp
```

### Dependencies

**Core Dependencies:**
- `mcp>=1.0.0` - MCP server framework
- No additional dependencies (uses Python standard library only)

## Usage

### Running the Server
```bash
# Using uv (recommended)
uv run python -m agent_memory

# Using uvx for one-time execution (local checkout)
uvx --from . python -m agent_memory

# Using uvx directly from GitHub (no checkout)
uvx --from "git+https://github.com/<owner>/<repo>.git@<ref>#subdirectory=mcp-tools/agent-memory" \
  python -m agent_memory

# Standard execution (if dependencies installed globally)
python -m agent_memory

# Test mode (development)
uv run python -m agent_memory --test
```

## MCP Server Configuration

### Using with Claude Desktop

1. **Install the server:**
   ```bash
  cd mcp-tools/agent-memory
   uv sync
   ```

2. **Add to Claude Desktop configuration:**

   Edit your Claude Desktop configuration file:
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Linux**: `~/.config/claude/claude_desktop_config.json`

   Add the Agent Memory server:
   ```json
   {
     "mcpServers": {
       "agent-memory": {
         "type": "stdio",
         "command": "uv",
         "args": ["run", "python", "-m", "agent_memory"],
         "cwd": "/absolute/path/to/your/mcp-tools/agent-memory"
       }
     }
   }
   ```

   **Important Notes:**
   - Use absolute paths for `cwd`
   - Ensure `uv sync` has been run in the project directory
   - Test the server works: `uv run python -m agent_memory --test`

3. **Restart Claude Desktop** to load the new server.

### Using with Other MCP Clients

For other MCP-compatible clients, run the server in stdio mode:
```bash
cd mcp-tools/agent-memory
uv run python -m agent_memory
```

The server communicates via JSON-RPC over stdin/stdout as per MCP specification.

### Using with uvx (Alternative)

For one-time usage without installation:
```bash
uvx --from /path/to/mcp-tools/agent-memory python -m agent_memory

# Or fetch directly from GitHub (no checkout)
uvx --from "git+https://github.com/<owner>/<repo>.git@<ref>#subdirectory=mcp-tools/agent-memory" \
  python -m agent_memory
```

## Repository Structure

Each consuming repository will contain (or allow creation of):

```
.github/
└─ agent-memory/
   └─ <agent-name>/
      ├─ logs/
      │  └─ YYYY-MM-DD.md
      ├─ _summary.md
      └─ _schema.md
```

## Memory Schema

### Default Schema (v1)

The schema defines the required structure of all session logs:

```markdown
# Agent Memory Schema v1

## Header
- Agent Name
- Date (YYYY-MM-DD)
- Session ID

## Context
- Project
- Focus Area
- Stage

## Discussion Summary
- Key topics discussed

## Decisions
- Explicit decisions made

## Open Questions
- Unresolved issues or risks

## Next Actions
- Follow-up actions
```

## Available Tools

### 1. `start_session`
Creates or opens a session log for an agent on a given date.

**Parameters:**
- `agent_name` (string, required): Logical agent identifier (e.g. `aristotle`)
- `repo_root` (string, required): Absolute path to repository root
- `date` (string, optional): Date in YYYY-MM-DD format (defaults to current date)

**Example:**
```json
{
  "agent_name": "aristotle",
  "repo_root": "/path/to/project"
}
```

### 2. `append_entry`
Appends structured content to a specific section of the session log.

**Parameters:**
- `agent_name` (string, required): Logical agent identifier
- `repo_root` (string, required): Absolute path to repository root
- `section` (string, required): Section name from schema
- `content` (string, required): Content to append
- `date` (string, optional): Date in YYYY-MM-DD format

**Allowed sections:**
- Context
- Discussion Summary
- Decisions
- Open Questions
- Next Actions

**Example:**
```json
{
  "agent_name": "aristotle",
  "repo_root": "/path/to/project",
  "section": "Decisions",
  "content": "Decided to use React for the frontend framework"
}
```

### 3. `read_summary`
Reads the canonical persistent summary for an agent.

**Parameters:**
- `agent_name` (string, required): Logical agent identifier
- `repo_root` (string, required): Absolute path to repository root

**Example:**
```json
{
  "agent_name": "aristotle",
  "repo_root": "/path/to/project"
}
```

### 4. `update_summary`
Updates a specific section of the agent summary.

**Parameters:**
- `agent_name` (string, required): Logical agent identifier
- `repo_root` (string, required): Absolute path to repository root
- `section` (string, required): Section name to update
- `content` (string, required): Content to add or replace
- `mode` (string, required): "append" or "replace"

**Example:**
```json
{
  "agent_name": "aristotle",
  "repo_root": "/path/to/project",
  "section": "Key Knowledge",
  "content": "Frontend architecture: React with TypeScript",
  "mode": "append"
}
```

### 5. `list_sessions`
Lists existing session logs for an agent.

**Parameters:**
- `agent_name` (string, required): Logical agent identifier
- `repo_root` (string, required): Absolute path to repository root
- `limit` (number, optional): Maximum number of sessions to return (1-100)

**Example:**
```json
{
  "agent_name": "aristotle",
  "repo_root": "/path/to/project",
  "limit": 10
}
```

## Available Resources

### `memory://schema-info`
Information about the agent memory schema, allowed sections, and design principles.

### `memory://server-status`
Current server status, configuration, capabilities, and safety features.

### `memory://usage-examples`
Example usage patterns and typical workflow for agent memory operations.

## Response Format

### Success Response
```json
{
  "ok": true,
  "data": {
    "session_file": "path/to/session.md",
    "created": true
  }
}
```

### Error Response
```json
{
  "ok": false,
  "code": "UserInput|Forbidden|NotFound|Timeout|Internal",
  "message": "Error description",
  "hint": "Suggested resolution",
  "correlation_id": "abc123"
}
```

## Error Codes

- **UserInput**: Invalid parameters, agent name, or section name
- **Forbidden**: Security violation (path traversal, invalid repository)
- **NotFound**: Repository, file, or section doesn't exist
- **Timeout**: Operation exceeded time limit
- **Internal**: Unexpected server error

## Intended Usage Pattern

1. **Agent session starts**
2. **Agent reads summary** via `read_summary`
3. **Human and agent reason together**
4. **Important outcomes persisted** via `append_entry`
5. **Durable knowledge curated** into summary via `update_summary`

## Example Workflow

```python
# Start a new session
{
  "tool": "start_session",
  "arguments": {
    "agent_name": "aristotle",
    "repo_root": "/path/to/project"
  }
}

# Read existing summary
{
  "tool": "read_summary",
  "arguments": {
    "agent_name": "aristotle",
    "repo_root": "/path/to/project"
  }
}

# Log important decision
{
  "tool": "append_entry",
  "arguments": {
    "agent_name": "aristotle",
    "repo_root": "/path/to/project",
    "section": "Decisions",
    "content": "Decided to use PostgreSQL for data persistence"
  }
}

# Update persistent summary
{
  "tool": "update_summary",
  "arguments": {
    "agent_name": "aristotle",
    "repo_root": "/path/to/project",
    "section": "Technical Decisions",
    "content": "Database: PostgreSQL chosen for ACID compliance",
    "mode": "append"
  }
}
```

## Safety Features

- **Path traversal protection**: Prevents access outside repository boundaries
- **Repository boundary enforcement**: All operations confined to specified repo root
- **Agent name validation**: Sanitizes agent names for filesystem safety
- **Content sanitization**: Limits content length and removes dangerous characters
- **Schema compliance checking**: Validates all writes against declared schema
- **No delete operations**: By design, no data removal capabilities
- **No network access**: Operates entirely on local filesystem
- **No arbitrary execution**: No shell command execution capabilities

## Limitations

- Maximum content length: 10KB per entry
- Agent names limited to 50 characters
- No delete operations supported (by design)
- No network access required or provided
- Memory limited to repository scope
- No automatic summarization or AI inference

## Development

### Project Structure
```
agent-memory/
├── src/agent_memory/
│   ├── __init__.py          # Package initialization
│   ├── __main__.py          # Entry point
│   ├── server.py           # MCP server setup
│   ├── tools.py            # Tool implementations
│   ├── memory_ops.py       # Core memory operations
│   ├── safety.py           # Security validation
│   └── errors.py           # Error handling
├── pyproject.toml          # Project configuration and dependencies
└── README.md              # Documentation
```

### Testing
```bash
# Run server tests
uv run python -m agent_memory --test

# Test specific functionality
uv run python -c "
import asyncio
from agent_memory.tools import tool_start_session
result = asyncio.run(tool_start_session({
    'agent_name': 'test_agent',
    'repo_root': '/tmp/test_repo'
}))
print(result)
"
```

## Architectural Note

This tool is intentionally **boring and deterministic**. That is a feature.

It provides a stable foundation upon which:
- Intelligent agents
- Agent SaaS platforms
- RAG systems
- Enterprise workflows

can be built safely and repeatedly.

The tool deliberately separates:
- **Reasoning** (LLMs / agents)
- **Persistence** (this MCP tool)
- **Judgment** (human-in-the-loop)

## Explicit Non-Goals

This tool does NOT:
- Generate summaries automatically
- Interpret or reason about content
- Decide what is important
- Store memory outside the repository
- Replace human judgment
- Provide AI-powered insights
- Execute arbitrary code
- Access network resources

## Troubleshooting

### VSCode MCP Issues

If you encounter "Unknown method" errors or connection issues:

1. **Test the server directly:**
   ```bash
  cd mcp-tools/agent-memory
   uv run python -m agent_memory --test
   ```

2. **Alternative VSCode configuration:**
   ```json
   {
     "mcpServers": {
       "agent-memory": {
         "type": "stdio",
         "command": "python",
         "args": ["-m", "agent_memory"],
         "cwd": "/absolute/path/to/mcp-tools/agent-memory",
         "env": {
           "UV_PROJECT_ENVIRONMENT": "/absolute/path/to/mcp-tools/agent-memory/.venv"
         }
       }
     }
   }
   ```

3. **Direct Python path (Windows example):**
   ```json
   {
     "mcpServers": {
       "agent-memory": {
         "type": "stdio",
         "command": "C:/path/to/mcp-tools/agent-memory/.venv/Scripts/python.exe",
         "args": ["-m", "agent_memory"],
         "cwd": "C:/path/to/mcp-tools/agent-memory"
       }
     }
   }
   ```

See `TROUBLESHOOTING.md` for detailed debugging steps.

### Core Functionality Test

Test without VSCode:
```bash
cd mcp-tools/agent-memory
uv run python -c "
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'src'))
import agent_memory.memory_ops as memory_ops

with tempfile.TemporaryDirectory() as td:
    manager = memory_ops.MemoryManager(td, 'test')
    print('✅ Memory manager works!')
    result = manager.start_session()
    print(f'✅ Session: {result[\"created\"]}')
"
```

## License

This MCP server is provided as-is for educational and development purposes.
