#!/usr/bin/env bash
# Install buildspec toolkit using pip

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CLAUDE_DIR="$HOME/.claude"

echo "Installing Buildspec Toolkit..."
echo ""

# 1. Install CLI via uv (global, editable mode)
echo "📦 Installing CLI with uv..."
if command -v uv >/dev/null 2>&1; then
  uv pip install -e "$PROJECT_ROOT"
  echo "✓ CLI installed via uv"
else
  echo "⚠️  uv not found, falling back to pip..."
  pip install -e "$PROJECT_ROOT"
  echo "✓ CLI installed via pip"
fi

# 2. Install Claude Code files
echo ""
echo "🔗 Installing Claude Code files..."
mkdir -p "$CLAUDE_DIR"/{agents,commands,hooks,mcp-servers,scripts,standards}

# Link agents (both .md and .json files)
for file in "$PROJECT_ROOT/claude_files/agents"/*.md; do
  [ -f "$file" ] && ln -sf "$file" "$CLAUDE_DIR/agents/"
done
for file in "$PROJECT_ROOT/claude_files/agents"/*.json; do
  [ -f "$file" ] && ln -sf "$file" "$CLAUDE_DIR/agents/"
done

# Link commands
for file in "$PROJECT_ROOT/claude_files/commands"/*.md; do
  [ -f "$file" ] && ln -sf "$file" "$CLAUDE_DIR/commands/"
done

# Link hooks
for file in "$PROJECT_ROOT/claude_files/hooks"/*.sh; do
  [ -f "$file" ] && ln -sf "$file" "$CLAUDE_DIR/hooks/" && chmod +x "$file"
done

# Link MCP servers
for file in "$PROJECT_ROOT/claude_files/mcp-servers"/*.py; do
  [ -f "$file" ] && ln -sf "$file" "$CLAUDE_DIR/mcp-servers/" && chmod +x "$file"
done

# Link scripts
for file in "$PROJECT_ROOT/claude_files/scripts"/*.sh; do
  [ -f "$file" ] && ln -sf "$file" "$CLAUDE_DIR/scripts/" && chmod +x "$file"
done

# Link standards
for file in "$PROJECT_ROOT/claude_files/standards"/*.md; do
  [ -f "$file" ] && ln -sf "$file" "$CLAUDE_DIR/standards/"
done

echo "✓ Claude Code files linked to $CLAUDE_DIR"

# 3. Verify installation
echo ""
if command -v buildspec >/dev/null 2>&1; then
  BUILDSPEC_PATH=$(which buildspec)
  echo "✅ Installation complete!"
  echo ""
  echo "Installed to: $BUILDSPEC_PATH"
  echo ""
else
  echo "⚠️  WARNING: 'buildspec' command not found in PATH"
  echo ""
  echo "This might happen if pip's bin directory is not in your PATH."
  echo "Common locations:"
  echo "  - ~/.local/bin/buildspec"
  echo "  - /usr/local/bin/buildspec"
  echo ""
  echo "Add to your ~/.bashrc or ~/.zshrc:"
  echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
  echo ""
fi

echo "The CLI auto-detects project context from .claude/ directory"
echo ""
echo "Available CLI commands:"
echo "  buildspec create-epic <planning-doc>"
echo "  buildspec create-tickets <epic-file>"
echo "  buildspec execute-epic <epic-file>"
echo "  buildspec execute-ticket <ticket-file>"
echo ""
echo "Available Claude Code commands:"
echo "  /create-epic <planning-doc>"
echo "  /create-tickets <epic-file>"
echo "  /execute-epic <epic-file>"
echo "  /execute-ticket <ticket-file>"
echo ""
echo "Try: buildspec --help"
