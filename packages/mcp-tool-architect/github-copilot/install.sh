#!/usr/bin/env bash
# Deploys this Copilot payload into a target repository's .github/ tree.
# Usage: ./install.sh [target-repo-path]   (defaults to current directory)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-$(pwd)}"

if [ ! -d "$TARGET" ]; then
  echo "Target directory does not exist: $TARGET" >&2
  exit 1
fi

installed=0
for sub in agents prompts; do
  if [ -d "$SCRIPT_DIR/$sub" ]; then
    mkdir -p "$TARGET/.github/$sub"
    cp -R "$SCRIPT_DIR/$sub/." "$TARGET/.github/$sub/"
    installed=$((installed + 1))
    echo "Installed $sub/ into $TARGET/.github/$sub/"
  fi
done

if [ "$installed" -eq 0 ]; then
  echo "Nothing to install (payload is empty)." >&2
  exit 1
fi
