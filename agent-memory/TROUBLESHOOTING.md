# Agent Memory MCP Server - Troubleshooting Guide

## Common Issues and Solutions

### "Unknown method" Error in VSCode

If you see an error like:
```
Error: MPC UserInput: Unknown method
```

This typically indicates a protocol-level issue between the MCP client and server.

#### Debugging Steps:

1. **Test the server directly:**

   **From GitHub:**
   ```bash
   uvx --from git+https://github.com/yourusername/agent-memory.git python -m agent_memory --test
   ```

   **From Local Clone:**
   ```bash
   cd agent-memory
   uv run python -m agent_memory --test
   ```

   This should show available tools and resources without errors.

2. **Check MCP library version:**
   ```bash
   uvx --from git+https://github.com/yourusername/agent-memory.git python -c "import mcp; print(mcp.__version__)"
   ```

3. **Test manual server startup:**

   **From GitHub:**
   ```bash
   uvx --from git+https://github.com/yourusername/agent-memory.git python -m agent_memory
   ```

   **From Local:**
   ```bash
   cd agent-memory
   uv run python -m agent_memory
   ```

   The server should start and show "Agent Memory MCP Server ready for connections"

4. **Verify tools are registered:**
   If the test passes, the server should show:
   ```
   Available tools: ['start_session', 'append_entry', 'read_summary', 'update_summary', 'list_sessions']
   Available resources: ['Memory Schema Information', 'Server Status', 'Usage Examples']
   ```

#### Solutions:

**Option 1: GitHub-based (Recommended)**
```json
{
  "mcpServers": {
    "agent-memory": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "git+https://github.com/yourusername/agent-memory.git", "python", "-m", "agent_memory"]
    }
  }
}
```

**Option 2: Local installation**
```bash
git clone https://github.com/yourusername/agent-memory.git
cd agent-memory
uv sync
uv run python -m agent_memory --test
```

Then use:
```json
{
  "mcpServers": {
    "agent-memory": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "python", "-m", "agent_memory"],
      "cwd": "/absolute/path/to/agent-memory"
    }
  }
}
```

**Option 3: Alternative local configuration**
```json
{
  "mcpServers": {
    "agent-memory": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "agent_memory"],
      "cwd": "/absolute/path/to/agent-memory",
      "env": {
        "UV_PROJECT_ENVIRONMENT": "/absolute/path/to/agent-memory/.venv"
      }
    }
  }
}
```

**Option 4: Direct Python path**
```json
{
  "mcpServers": {
    "agent-memory": {
      "type": "stdio",
      "command": "/absolute/path/to/agent-memory/.venv/Scripts/python.exe",
      "args": ["-m", "agent_memory"],
      "cwd": "/absolute/path/to/agent-memory"
    }
  }
}
```

### Environment Setup Issues

1. **Missing dependencies:**
   ```bash
   cd agent-memory
   uv sync
   ```

2. **Python path issues:**
   Ensure you're in the correct directory and uv is installed:
   ```bash
   which uv
   uv --version
   ```

### Testing Without VSCode

You can test the tool functionality directly:

**From GitHub:**
```bash
uvx --from git+https://github.com/yourusername/agent-memory.git python -c "
import tempfile
import agent_memory.memory_ops as memory_ops

# Test basic functionality
with tempfile.TemporaryDirectory() as td:
    manager = memory_ops.MemoryManager(td, 'test_agent')
    print('Memory manager initialized successfully')

    result = manager.start_session()
    print(f'Session started: {result}')

    result = manager.append_entry('Context', 'Test entry')
    print('Entry appended successfully')

print('✅ Core functionality works!')
"
```

**From Local Clone:**
```bash
cd agent-memory
uv run python -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'src'))

import tempfile
import agent_memory.memory_ops as memory_ops

# Test basic functionality
with tempfile.TemporaryDirectory() as td:
    manager = memory_ops.MemoryManager(td, 'test_agent')
    print('Memory manager initialized successfully')

    result = manager.start_session()
    print(f'Session started: {result}')

    result = manager.append_entry('Context', 'Test entry')
    print('Entry appended successfully')

print('✅ Core functionality works!')
"
```

## Log Files

Check these locations for additional debugging information:

- VSCode Developer Console (Help → Toggle Developer Tools)
- MCP server stderr output
- System logs

## Getting Help

If none of these solutions work:

1. Verify the pdf-reader MCP server works in your environment
2. Check VSCode MCP extension logs
3. Try running with different Python versions
4. Check file permissions in the agent-memory directory

## Working Configuration Example

Here are confirmed working configurations:

**GitHub-based (Recommended - no local setup needed):**
```json
{
  "mcpServers": {
    "agent-memory": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "git+https://github.com/yourusername/agent-memory.git", "python", "-m", "agent_memory"]
    }
  }
}
```

**Local installation:**
```json
{
  "mcpServers": {
    "agent-memory": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "python", "-m", "agent_memory"],
      "cwd": "/absolute/path/to/agent-memory"
    }
  }
}
```

**Testing:**
- GitHub version: `uvx --from git+https://github.com/yourusername/agent-memory.git python -m agent_memory --test`
- Local version: `uv run python -m agent_memory --test` (after `uv sync`)

**Benefits of GitHub-based approach:**
- No local cloning required
- Always uses latest version
- No dependency management needed
- Works from any machine with `uvx`
