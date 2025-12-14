#!/bin/bash

# Post-create script for Maruti dev container
# This script runs after the container is created

set -e

echo "🚀 Setting up Maruti development environment..."

# Ensure we're in the right directory
cd /app

# Install dependencies if not already done
echo "📦 Installing workspace dependencies..."
uv sync --dev

# Auto-discover and install all MCP servers in editable mode
echo "🔧 Auto-discovering and installing MCP servers..."
mcp_count=0
for dir in */; do
    # Check if directory contains a pyproject.toml with MCP-related content
    if [ -f "${dir}pyproject.toml" ] && [ "$dir" != ".devcontainer/" ]; then
        if grep -q "mcp\|Model Context Protocol" "${dir}pyproject.toml" 2>/dev/null; then
            echo "  📦 Installing MCP server: ${dir%/}"
            cd "$dir" && uv pip install -e . && cd ..
            echo "  ✅ ${dir%/} installed successfully"
            ((mcp_count++))
        fi
    fi
done

if [ $mcp_count -eq 0 ]; then
    echo "  ⚠️  No MCP servers found to install"
else
    echo "  🎉 Successfully installed $mcp_count MCP server(s)"
fi

# Set up git safe directory
echo "🔧 Configuring Git..."
git config --global --add safe.directory /app

# Create useful aliases
echo "⚡ Creating helpful aliases..."
cat << 'EOF' >> ~/.bashrc

# Maruti project aliases
alias ll='ls -la'
alias la='ls -A'
alias l='ls -CF'
alias ..='cd ..'
alias ...='cd ../..'

# UV shortcuts
alias uv-sync='uv sync --dev'
alias uv-add='uv add'
alias uv-run='uv run'

# Python shortcuts
alias py='python'
alias python='uv run python'
alias pip='uv pip'

# MCP server shortcuts
alias pdf-server='uv run pdf-reader'
alias xlsx-server='uv run xlsx-reader'
alias onenote-server='uv run onenote-reader'

# Testing shortcuts
alias test='uv run pytest'
alias test-pdf='uv run pytest pdf-reader/test_pdf.py -v'
alias test-xlsx='uv run pytest xlsx-reader/test_server.py -v'

# Project info
alias project-info='echo "Maruti MCP Servers Project" && echo "==========================" && echo "PDF Reader: uv run pdf-reader" && echo "XLSX Reader: uv run xlsx-reader" && echo "OneNote Reader: uv run onenote-reader" && echo "Run Tests: uv run pytest" && echo "Add Package: uv add <package>" && echo "Sync Dependencies: uv sync --dev"'

EOF

# Make sure the virtual environment is properly set up
echo "🐍 Setting up Python environment..."
if [ ! -f /app/.venv/bin/python ]; then
    echo "Creating virtual environment..."
    uv venv
fi

# Verify installation
echo "✅ Verifying installation..."
uv run python --version
echo "UV version: $(uv --version)"

# Display helpful information
echo ""
echo "🎉 Maruti dev container setup complete!"
echo ""
echo "Available commands:"
echo "  pdf-server      - Start PDF MCP server"
echo "  xlsx-server     - Start XLSX MCP server"
echo "  onenote-server  - Start OneNote MCP server"
echo "  test           - Run all tests"
echo "  test-pdf       - Run PDF tests"
echo "  test-xlsx      - Run XLSX tests"
echo "  project-info   - Show project information"
echo ""
echo "🔧 MCP Generator Mode Workflow:"
echo "  1. Use MCP Generator mode to create new servers"
echo "  2. New servers are auto-discovered and installed"
echo "  3. No manual dependency installation needed!"
echo "  4. Rebuild container if needed: Ctrl+Shift+P -> 'Rebuild Container'"
echo ""
echo "📋 Current MCP Servers:"
for dir in */; do
    if [ -f "${dir}pyproject.toml" ] && [ "$dir" != ".devcontainer/" ]; then
        if grep -q "mcp\|Model Context Protocol" "${dir}pyproject.toml" 2>/dev/null; then
            echo "  ✅ ${dir%/}"
        fi
    fi
done
echo ""
echo "Happy coding! 🚀"
