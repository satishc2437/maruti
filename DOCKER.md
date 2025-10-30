# Maruti Docker Development Environment

This document describes how to set up and use the Docker development environment for the Maruti project.

## Prerequisites

- Docker Desktop for Windows (with Linux containers support - default)
- Docker Compose
- PowerShell 5.1 or later (or Bash if on Linux/WSL)

## Quick Start

1. **Build the development image:**
   ```powershell
   .\docker-dev.ps1 build
   ```

2. **Start the development container:**
   ```powershell
   .\docker-dev.ps1 start
   ```

3. **Connect to the development environment:**
   ```powershell
   .\docker-dev.ps1 shell
   ```

4. **Inside the container, you can:**
   ```bash
   # Install dependencies
   uv sync --dev
   
   # Run individual MCP servers
   uv run pdf-reader
   uv run xlsx-reader
   uv run onenote-reader
   
   # Run tests
   uv run pytest pdf-reader/test_pdf.py
   uv run pytest xlsx-reader/test_server.py
   
   # Add new dependencies
   uv add <package-name>
   
   # Add development dependencies
   uv add --dev <package-name>
   ```

## Docker Helper Script

The `docker-dev.ps1` script provides convenient commands for managing the development environment:

### Available Commands

| Command | Description |
|---------|-------------|
| `build` | Build the Docker image |
| `start` | Start the development container |
| `stop` | Stop the development container |
| `restart` | Restart the development container |
| `shell` | Connect to the container shell |
| `logs` | Show container logs |
| `test` | Run tests in a separate container |
| `clean` | Remove containers and images |
| `status` | Show container status |
| `help` | Show help message |

### Usage Examples

```powershell
# Build and start the environment
.\docker-dev.ps1 build
.\docker-dev.ps1 start

# Connect to work on the project
.\docker-dev.ps1 shell

# View logs if something goes wrong
.\docker-dev.ps1 logs

# Run tests
.\docker-dev.ps1 test

# Clean up when done
.\docker-dev.ps1 clean
```

## Container Features

### Python Environment
- **Python 3.13** (latest)
- **UV package manager** for fast dependency management
- **All project dependencies** pre-installed

### Development Tools
- **Git** for version control
- **Vim/Nano** for text editing
- **Bash** as the default shell

### Ports Exposed
- `8000`: MCP servers
- `8080`: Alternative web server
- `3000`: Frontend development
- `5000`: Flask/FastAPI development

### Volumes
- **Project directory**: Live-mounted for real-time development
- **UV cache**: Persistent package cache for faster installs
- **Git config**: Persistent Git configuration

## Development Workflow

1. **Make changes** to your code on the host machine using your preferred editor (VS Code, etc.)
2. **Changes are immediately reflected** in the container due to volume mounting
3. **Test your changes** by running commands inside the container
4. **Commit changes** from either the host or container (Git is available in both)

## Project Structure in Container

```
/app/
├── pdf-reader/          # PDF MCP server
├── onenote-reader/      # OneNote MCP server  
├── xlsx-reader/         # Excel MCP server
├── pyproject.toml       # Workspace configuration
├── .venv/               # Virtual environment (managed by UV)
└── ...                  # Other project files
```

## Running Individual Services

Each MCP server can be run independently:

```bash
# PDF Reader MCP Server
uv run pdf-reader

# XLSX Reader MCP Server  
uv run xlsx-reader

# OneNote Reader MCP Server
uv run onenote-reader
```

## Testing

Run tests using the test profile:

```powershell
# Run all tests
.\docker-dev.ps1 test

# Or run specific tests inside the container
.\docker-dev.ps1 shell
uv run pytest pdf-reader/test_pdf.py -v
uv run pytest xlsx-reader/test_server.py -v
```

## Troubleshooting

### Container Won't Start
```powershell
# Check container status
.\docker-dev.ps1 status

# View logs for errors
.\docker-dev.ps1 logs

# Clean and rebuild
.\docker-dev.ps1 clean
.\docker-dev.ps1 build
```

### Python Dependencies Issues
```bash
# Inside the container, resync dependencies
uv sync --dev --refresh

# Or install specific packages
uv add <package-name>
```

### Performance Issues
- Ensure Docker Desktop has sufficient resources allocated
- Consider using Docker volumes instead of bind mounts for better performance
- The UV cache volume should speed up subsequent dependency installations

## Environment Variables

The container sets these important environment variables:

- `PYTHONPATH=/app`: Ensures Python can find your modules
- `UV_PROJECT_ENVIRONMENT=/app/.venv`: UV virtual environment location
- `PYTHONUNBUFFERED=1`: Ensures Python output is not buffered

## Security Notes

- The container runs with standard user privileges
- No sensitive data should be hardcoded in the Dockerfile
- Use environment variables or mounted secrets for sensitive configuration

## Customization

To customize the development environment:

1. **Modify `Dockerfile`** for system-level changes
2. **Update `docker-compose.yml`** for service configuration
3. **Edit `docker-dev.ps1`** to add new helper commands
4. **Update `.dockerignore`** to exclude additional files from the build context