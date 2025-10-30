# Maruti Dev Container Setup

This directory contains the development container configuration for the Maruti project.

## What is a Dev Container?

A development container (dev container) is a running Docker container with a well-defined tool/runtime stack and its prerequisites. It allows you to use a container as a full-featured development environment.

## Features

- **Consistent Environment**: Same Python 3.13 environment across all development machines
- **Pre-configured VS Code**: Extensions, settings, and tools ready to go
- **Integrated Terminal**: Full bash environment with all project dependencies
- **Port Forwarding**: Automatic forwarding of development ports (8000, 8080, 3000, 5000)
- **Git Integration**: Git configuration preserved and working
- **Fast Setup**: One-click environment setup

## Getting Started

### Prerequisites
- Visual Studio Code
- Docker Desktop
- Dev Containers extension for VS Code (`ms-vscode-remote.remote-containers`)

### Opening in Dev Container

1. **Clone the repository** (if you haven't already):
   ```bash
   git clone https://github.com/satishc2437/maruti.git
   cd maruti
   ```

2. **Open in VS Code**:
   ```bash
   code .
   ```

3. **Reopen in Container**:
   - Press `F1` or `Ctrl+Shift+P`
   - Type "Dev Containers: Reopen in Container"
   - Select the command and wait for the container to build

   **OR**

   - VS Code should show a notification asking to "Reopen in Container"
   - Click "Reopen in Container"

4. **Wait for Setup**:
   - The container will build (first time takes a few minutes)
   - Dependencies will be installed automatically
   - VS Code will be configured with Python extensions

### What Happens During Setup

1. **Container Build**: Docker builds the development environment
2. **Dependency Installation**: UV installs all project dependencies
3. **VS Code Configuration**: Extensions and settings are applied
4. **Environment Setup**: Python paths and virtual environment configured

## Development Workflow

Once the dev container is running:

### Running MCP Servers
```bash
# PDF Reader MCP Server
uv run pdf-reader

# XLSX Reader MCP Server  
uv run xlsx-reader

# OneNote Reader MCP Server
uv run onenote-reader
```

### Running Tests
```bash
# Run specific tests
uv run pytest pdf-reader/test_pdf.py -v
uv run pytest xlsx-reader/test_server.py -v

# Run all tests
uv run pytest
```

### Adding Dependencies
```bash
# Add regular dependency
uv add <package-name>

# Add development dependency
uv add --dev <package-name>

# Sync dependencies
uv sync --dev
```

### Working with Git
Git is fully configured and your local Git settings are preserved:
```bash
git status
git add .
git commit -m "Your changes"
git push
```

## VS Code Extensions Included

The dev container comes pre-configured with essential extensions:

- **Python Support**: `ms-python.python`
- **Code Formatting**: `ms-python.black-formatter`, `ms-python.isort`
- **Linting**: `ms-python.pylint`
- **Jupyter**: `ms-toolsai.jupyter`
- **Git Integration**: `eamodio.gitlens`
- **Docker**: `ms-vscode.docker`
- **GitHub Copilot**: `GitHub.copilot`, `GitHub.copilot-chat`

## Port Forwarding

The following ports are automatically forwarded:

| Port | Purpose | Auto-Forward |
|------|---------|--------------|
| 8000 | MCP Server | Notify |
| 8080 | Alt Web Server | Silent |
| 3000 | Frontend Dev | Silent |
| 5000 | Flask/FastAPI | Silent |

## Persistent Data

- **UV Cache**: Package cache is stored in a Docker volume for faster rebuilds
- **Git History**: Your Git repository is mounted, preserving history
- **VS Code Settings**: Container-specific settings are applied

## Troubleshooting

### Container Won't Start
1. Ensure Docker Desktop is running
2. Check Docker has sufficient resources allocated
3. Try rebuilding: `F1` → "Dev Containers: Rebuild Container"

### Python/Dependencies Issues
```bash
# Reinstall dependencies
uv sync --dev --refresh

# Check Python environment
which python
python --version
```

### VS Code Extension Issues
```bash
# Reload VS Code window
F1 → "Developer: Reload Window"

# Rebuild container with fresh extensions
F1 → "Dev Containers: Rebuild Container Without Cache"
```

### Git Issues
```bash
# If you see safe directory warnings
git config --global --add safe.directory /app
```

## Customization

### Adding VS Code Extensions
Edit `.devcontainer/devcontainer.json` and add extension IDs to the `extensions` array:
```json
"extensions": [
    "existing.extension",
    "new.extension.id"
]
```

### Changing Python Settings
Modify the `settings` section in `devcontainer.json`:
```json
"settings": {
    "python.linting.pylintEnabled": false,
    "python.formatting.provider": "autopep8"
}
```

### Adding System Packages
Edit `.devcontainer/Dockerfile` and add packages to the `apt-get install` command:
```dockerfile
RUN apt-get update && apt-get install -y \
    existing-package \
    new-package \
    && rm -rf /var/lib/apt/lists/*
```

## Performance Tips

1. **Use .dockerignore**: Large files/directories are already excluded
2. **Layer Caching**: Dependencies are installed before code copy for better caching
3. **Volume Mounts**: UV cache is persisted across container rebuilds
4. **Minimal Base Image**: Using `python:3.13-slim` for smaller image size

## Comparison with Regular Docker

| Feature | Dev Container | Regular Docker |
|---------|---------------|----------------|
| VS Code Integration | ✅ Native | ❌ Manual setup |
| Extension Management | ✅ Automatic | ❌ Manual |
| Port Forwarding | ✅ Automatic | ❌ Manual `-p` flags |
| Git Integration | ✅ Seamless | ❌ Complex setup |
| Debugging | ✅ Built-in | ❌ Additional config |
| IntelliSense | ✅ Full support | ❌ Limited |

The dev container approach provides a more integrated development experience compared to regular Docker containers, especially when using VS Code as your primary editor.