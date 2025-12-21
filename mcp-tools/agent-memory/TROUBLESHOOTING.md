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
   ```bash
  cd mcp-tools/agent-memory
   uv run python -m agent_memory --test
   ```
   This should show available tools and resources without errors.

2. **Check MCP library version:**
   ```bash
   uv run python -c "import mcp; print(mcp.__version__)"
   ```

3. **Test manual server startup:**
   ```bash
  cd mcp-tools/agent-memory
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

**Option 1: Update MCP library**
```bash
cd mcp-tools/agent-memory
uv add mcp --upgrade
```

**Option 2: Alternative VSCode configuration**
Try this configuration instead:
```json
{
  "mcpServers": {
    "agent-memory": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "agent_memory"],
      "cwd": "Q:/repos/maruti/mcp-tools/agent-memory",
      "env": {
        "UV_PROJECT_ENVIRONMENT": "Q:/repos/maruti/mcp-tools/agent-memory/.venv"
      }
    }
  }
}
```

**Option 3: Use direct Python path**
```json
{
  "mcpServers": {
    "agent-memory": {
      "type": "stdio",
      "command": "Q:/repos/maruti/mcp-tools/agent-memory/.venv/Scripts/python.exe",
      "args": ["-m", "agent_memory"],
      "cwd": "Q:/repos/maruti/mcp-tools/agent-memory"
    }
  }
}
```

**Option 4: Install dependencies first**
```bash
cd Q:/repos/maruti/mcp-tools/agent-memory
uv sync
uv run python -m agent_memory --test
```

### Environment Setup Issues

1. **Missing dependencies:**
   ```bash
  cd mcp-tools/agent-memory
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

```bash
cd mcp-tools/agent-memory
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

Here's a confirmed working configuration:

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

Make sure:
- The `cwd` path is absolute and correct
- You've run `uv sync` in the directory
- The test command works: `uv run python -m agent_memory --test`
