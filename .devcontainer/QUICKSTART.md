# 🚀 Maruti Dev Container - Quick Start Guide

Welcome to the Maruti project! This guide will get you up and running with the dev container in just a few steps.

## 🎯 What You'll Get

- **Instant Environment**: Python 3.14 + all dependencies pre-installed
- **VS Code Integration**: Extensions, settings, and debugging ready
- **MCP Servers**: PDF, XLSX, and Agent-Memory readers ready to run
- **Testing Setup**: Pytest configured and ready
- **Code Quality**: Black, isort, and pylint pre-configured

## 📋 Prerequisites

Make sure you have these installed:
- ✅ [Visual Studio Code](https://code.visualstudio.com/)
- ✅ [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- ✅ [Dev Containers Extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

## 🚀 Getting Started

### Step 1: Open the Project
```bash
# If you haven't cloned yet
git clone https://github.com/satishc2437/maruti.git
cd maruti

# Open in VS Code
code .
```

### Step 2: Open in Dev Container
When VS Code opens, you should see a notification:
> **"Folder contains a Dev Container configuration file. Reopen folder to develop in a container"**

Click **"Reopen in Container"**

**OR** manually trigger it:
1. Press `F1` (or `Ctrl+Shift+P`)
2. Type: `Dev Containers: Reopen in Container`
3. Press Enter

### Step 3: Wait for Setup
The first time will take a few minutes:
- 📦 Building container image
- 🐍 Installing Python dependencies
- 🔧 Configuring VS Code extensions
- ✨ Running setup scripts

You'll see progress in the VS Code notification area.

### Step 4: Verify Setup
Once complete, open a terminal in VS Code (`Ctrl+`` ` `) and run:
```bash
project-info
```

You should see the project information and available commands.

## 🎮 Using the Development Environment

### Running MCP Servers
Use the convenient aliases:
```bash
pdf-server      # Start PDF MCP server
xlsx-server     # Start XLSX MCP server
```

Or use VS Code tasks (`Ctrl+Shift+P` → `Tasks: Run Task`):
- `Run: PDF Reader MCP Server`
- `Run: XLSX Reader MCP Server`

### Running Tests
```bash
test           # Run all tests
test-pdf       # Run PDF reader tests
test-xlsx      # Run XLSX reader tests
```

Or use VS Code tasks:
- `Test: All`
- `Test: PDF Reader`
- `Test: XLSX Reader`

### Debugging
1. Open a Python file
2. Set breakpoints (click left margin)
3. Press `F5` or go to Run & Debug panel
4. Choose your debug configuration:
   - `PDF Reader MCP Server`
   - `XLSX Reader MCP Server`
   - `Python: Current File`

### Adding Dependencies
```bash
uv add <package-name>        # Add regular dependency
uv add --dev <package-name>  # Add dev dependency
uv-sync                      # Sync all dependencies
```

### Code Formatting & Linting
- **Auto-format on save**: Already enabled
- **Manual formatting**: `Ctrl+Shift+P` → `Format Document`
- **Run linting**: Use task `Lint: PyLint`

## 🔧 Customizing Your Environment

### Adding VS Code Extensions
Edit `.devcontainer/devcontainer.json`:
```json
"extensions": [
    "existing.extension",
    "your.new.extension"
]
```

### Changing Python Settings
Modify settings in `.devcontainer/devcontainer.json`:
```json
"settings": {
    "python.linting.pylintEnabled": false,
    "python.formatting.provider": "autopep8"
}
```

### Adding System Packages
Edit `.devcontainer/Dockerfile`:
```dockerfile
RUN apt-get update && apt-get install -y \
    existing-package \
    your-new-package \
    && rm -rf /var/lib/apt/lists/*
```

## 🆘 Troubleshooting

### Container Won't Start
1. **Check Docker**: Ensure Docker Desktop is running
2. **Resources**: Make sure Docker has enough CPU/memory allocated
3. **Rebuild**: `F1` → `Dev Containers: Rebuild Container`

### VS Code Issues
1. **Reload Window**: `F1` → `Developer: Reload Window`
2. **Extension Issues**: `F1` → `Dev Containers: Rebuild Container Without Cache`

### Python/Dependencies Issues
```bash
# Refresh dependencies
uv sync --dev --refresh

# Check Python setup
which python
python --version
uv --version
```

### Git Issues
```bash
# Fix safe directory warnings
git config --global --add safe.directory /app
```

## 💡 Pro Tips

### Performance
- **First build is slow**: Subsequent starts are much faster
- **Use .dockerignore**: Keep build context small
- **Layer caching**: Dependencies are cached separately from code

### Development Workflow
1. **Make changes** in VS Code (files auto-save)
2. **Test immediately** with `test` command
3. **Debug easily** with F5
4. **Commit from container** (Git works normally)

### Useful Keyboard Shortcuts
- `Ctrl+`` ` - Open terminal
- `F5` - Start debugging
- `Ctrl+Shift+P` - Command palette
- `Ctrl+Shift+E` - Explorer
- `Ctrl+Shift+G` - Source control

### Built-in Commands
All these commands are available in the terminal:
```bash
project-info    # Show project overview
ll              # List files (ls -la)
py              # Python shortcut
test            # Run pytest
uv-sync         # Sync dependencies
pdf-server      # Start PDF server
xlsx-server     # Start XLSX server
```

## 🎉 You're Ready!

Your Maruti development environment is now fully configured and ready for productive development. The dev container approach ensures everyone on your team has the exact same development environment, eliminating "works on my machine" issues.

Happy coding! 🚀

## 📚 Additional Resources

- [Dev Container Documentation](https://containers.dev/)
- [VS Code Dev Containers](https://code.visualstudio.com/docs/devcontainers/containers)
- [UV Package Manager](https://docs.astral.sh/uv/)
- [MCP Protocol](https://modelcontextprotocol.io/)
