# MCP Development Workflow

This workspace is configured to automatically handle MCP server development with zero manual dependency management.

## 🚀 Creating New MCP Servers

### Using MCP Generator Mode

1. **Switch to MCP Generator Mode** in your current session
2. **Describe your MCP server** in natural language
3. **Let MCP Generator create the complete server structure**
4. **The server is automatically integrated** into the workspace

### What Happens Automatically

✅ **Auto-Discovery**: New MCP servers are automatically detected
✅ **Auto-Installation**: Dependencies installed in editable mode
✅ **Auto-Integration**: Added to workspace configuration
✅ **Auto-Testing**: Test scripts work immediately

## 🔧 DevContainer Integration

### Current Auto-Discovery Logic

The DevContainer automatically finds and installs any directory containing:
- A `pyproject.toml` file
- References to "mcp" or "Model Context Protocol" in the project file

### Files Modified for Auto-Discovery

1. **`.devcontainer/Dockerfile`** - Build-time MCP server installation
2. **`.devcontainer/post-create.sh`** - Runtime MCP server setup
3. **`.devcontainer/add-mcp-server.sh`** - Helper script for manual additions

## 📋 Current MCP Servers

| Server | Status | Description |
|--------|--------|-------------|
| pdf-reader | ✅ Active | PDF processing and content extraction |
| xlsx-reader | ✅ Active | Excel workbook reading and editing |
| onenote-reader | ✅ Active | OneNote integration (scaffold phase) |
| agent-memory | ✅ Active | Deterministic repository-backed agent memory |

## 🛠️ Development Commands

### Server Management
```bash
# Start any MCP server
uv run <server-name>

# Examples:
uv run pdf-reader
uv run xlsx-reader
uv run onenote-reader
```

### Testing
```bash
# Run server-specific tests
cd mcp-tools/<server-name> && python test_*.py

# Examples:
cd mcp-tools/pdf-reader && python test_pdf.py
cd mcp-tools/xlsx-reader && python test_server.py
```

### Workspace Management
```bash
# Sync all dependencies
uv sync --dev

# Rebuild container to pick up new servers
# Ctrl+Shift+P -> "Rebuild Container"
```

## 🔄 Workflow for New Servers

### Step 1: Create with MCP Generator
```
Use MCP Generator mode to describe and create your server
Example: "Create an MCP server that processes images and extracts metadata"
```

### Step 2: Automatic Integration
- Server is created in new directory (e.g., `mcp-tools/image-processor/`)
- DevContainer detects the new server automatically
- Dependencies are installed in editable mode
- Server is immediately runnable

### Step 3: Development Ready
```bash
# Server is immediately available
uv run image-processor

# Tests work immediately
cd mcp-tools/image-processor && python test_*.py
```

## 🚨 Troubleshooting

### If New Server Not Detected
1. Ensure `pyproject.toml` exists in server directory
2. Verify "mcp" is mentioned in the project file
3. Rebuild DevContainer: Ctrl+Shift+P → "Rebuild Container"

### Manual Server Addition
```bash
# If needed, manually add to workspace
.devcontainer/add-mcp-server.sh <server-name>
```

### Re-run Setup
```bash
# Re-run post-create setup
.devcontainer/post-create.sh
```

## 📖 Best Practices

1. **Use MCP Generator Mode** for all new servers
2. **Let auto-discovery handle integration** - no manual steps needed
3. **Include tests** in your server description to MCP Generator
4. **Rebuild container** if servers aren't detected
5. **Follow naming convention**: lowercase with hyphens (e.g., `text-analyzer`)

## 🎯 Benefits

- **Zero Manual Setup**: No dependency installation needed
- **Consistent Structure**: All servers follow same patterns
- **Immediate Testing**: Tests work right after creation
- **Easy Scaling**: Add unlimited servers without configuration changes
- **Development Speed**: Focus on logic, not setup

---

*This workflow ensures that using MCP Generator mode results in immediately functional, fully integrated MCP servers with zero manual dependency management.*
