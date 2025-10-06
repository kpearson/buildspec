#!/usr/bin/env bash
# Uninstall buildspec toolkit

set -e

CLAUDE_DIR="$HOME/.claude"

echo "Removing Buildspec Toolkit..."
echo ""

# 1. Uninstall CLI via pip
echo "📦 Uninstalling CLI..."
if pip show buildspec-cli >/dev/null 2>&1; then
    pip uninstall -y buildspec-cli
    echo "✓ CLI uninstalled"
else
    echo "  Package 'buildspec-cli' not found (may have been manually removed)"
fi

# 2. Remove Claude Code files
echo ""
echo "🔗 Removing Claude Code files..."

# Remove agents
for file in create-epic.md create-epic-v2.md epic-generator.md; do
    if [ -L "$CLAUDE_DIR/agents/$file" ]; then
        rm "$CLAUDE_DIR/agents/$file"
    fi
done

# Remove commands
for file in create-epic.md create-tickets.md execute-epic.md execute-ticket.md; do
    if [ -L "$CLAUDE_DIR/commands/$file" ]; then
        rm "$CLAUDE_DIR/commands/$file"
    fi
done

# Remove hooks
for file in validate-epic-creation.sh; do
    if [ -L "$CLAUDE_DIR/hooks/$file" ]; then
        rm "$CLAUDE_DIR/hooks/$file"
    fi
done

# Remove MCP servers
for file in epic-validator.py; do
    if [ -L "$CLAUDE_DIR/mcp-servers/$file" ]; then
        rm "$CLAUDE_DIR/mcp-servers/$file"
    fi
done

# Remove scripts
for file in epic-paths.sh validate-epic.sh; do
    if [ -L "$CLAUDE_DIR/scripts/$file" ]; then
        rm "$CLAUDE_DIR/scripts/$file"
    fi
done

echo "✓ Claude Code files removed"
echo ""
echo "✅ Buildspec toolkit uninstalled"
