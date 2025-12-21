# Agent Memory MCP - GitHub Setup Guide

## Quick Start (No Local Clone Required)

### VSCode MCP Configuration

Add this to your Claude Desktop `mcp.json` configuration:

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

**Replace `yourusername` with the actual GitHub username/organization.**

### Test from Command Line

```bash
# Test the server
uvx --from git+https://github.com/yourusername/agent-memory.git python -m agent_memory --test

# Run the server manually
uvx --from git+https://github.com/yourusername/agent-memory.git python -m agent_memory
```

## Configuration Files

### Windows
```
%APPDATA%\Claude\claude_desktop_config.json
```

### macOS
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

### Linux
```
~/.config/claude/claude_desktop_config.json
```

## Benefits of GitHub-based Setup

- ✅ **No local cloning required**
- ✅ **Always uses latest version**
- ✅ **No dependency management**
- ✅ **Works from any machine with uvx**
- ✅ **Automatic updates**

## Example Usage

Once configured, you can use these tools in Claude Desktop:

1. **start_session** - Create new memory session
2. **append_entry** - Add to memory sections
3. **read_summary** - Read persistent summary
4. **update_summary** - Update summary sections
5. **list_sessions** - List available sessions

## Repository Structure Created

The tool will create this structure in your repositories:

```
your-project/
├── .github/
│   └── mcp-tools/agent-memory/
│       └── <agent-name>/
│           ├── logs/
│           │   └── YYYY-MM-DD.md
│           ├── _summary.md
│           └── _schema.md
```

## Troubleshooting

If you encounter issues, see `TROUBLESHOOTING.md` for detailed debugging steps.

**Quick test:**
```bash
uvx --from git+https://github.com/yourusername/agent-memory.git python -m agent_memory --test
```

Should show:
```
Available tools: ['start_session', 'append_entry', 'read_summary', 'update_summary', 'list_sessions']
