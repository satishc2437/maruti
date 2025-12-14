#!/bin/bash

# Helper script to add a new MCP server to the workspace
# Usage: ./add-mcp-server.sh <server-name>

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <server-name>"
    echo "Example: $0 text-analyzer"
    exit 1
fi

SERVER_NAME="$1"
echo "🚀 Adding new MCP server: $SERVER_NAME"

# Check if server directory already exists
if [ -d "$SERVER_NAME" ]; then
    echo "❌ Directory '$SERVER_NAME' already exists!"
    exit 1
fi

# Update workspace members in root pyproject.toml
echo "📝 Updating workspace configuration..."
if ! grep -q "\"$SERVER_NAME\"" pyproject.toml; then
    # Add to workspace members
    sed -i "/members = \[/,/\]/ s/\]/    \"$SERVER_NAME\",\n\]/" pyproject.toml
    echo "  ✅ Added '$SERVER_NAME' to workspace members"
else
    echo "  ⚠️  '$SERVER_NAME' already in workspace members"
fi

# The MCP server directory and files should be created by MCP Generator mode
# This script just ensures workspace integration

echo "🎉 Workspace updated for new MCP server: $SERVER_NAME"
echo ""
echo "Next steps:"
echo "1. Use MCP Generator mode to create the server implementation"
echo "2. Rebuild DevContainer to auto-install the new server"
echo "3. The server will be automatically discovered and installed"
echo ""
echo "Available after rebuild:"
echo "  uv run $SERVER_NAME                    # Start the server"
echo "  cd $SERVER_NAME && python test_*.py   # Run tests (if created)"
