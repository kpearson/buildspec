# Buildspec Portability Guide

## ✅ Cross-Platform Compatibility

This toolkit is designed to work on **any Unix-based system** (Linux, macOS,
BSD) where Claude Code is installed.

## System Requirements

### Required

- **Unix-based OS**: Linux, macOS, or BSD
- **Bash shell**: Version 3.2+ (macOS default) or 4.0+ (Linux)
- **Python**: 3.8 or higher
- **pip**: Python package installer
- **Claude Code CLI**: Installed and in PATH
- **Git**: For version control and branch management
- **GitHub CLI** (`gh`): For PR creation (optional but recommended)

### Optional

- **jq**: For JSON parsing in hooks (used by validation hooks)

## Installation on Any Machine

### Quick Install

```bash
# Clone to any location on your system
git clone https://github.com/you/buildspec.git ~/tools/buildspec
cd ~/tools/buildspec

# Install (works on any Unix system)
make install
```

### What Gets Installed

1. **CLI binary** (via pip):
   - Installed to: `~/.local/bin/buildspec` (or system pip location)
   - Editable install: changes to code apply instantly
   - Works from any directory

2. **Claude Code files** (via symlinks):
   - Symlinked to: `~/.claude/`
   - Portable paths using `$HOME` and `~/` notation
   - No hardcoded user directories

## Portable Path Strategy

All scripts use **portable path resolution**:

✅ **Good** (Portable):

```bash
$HOME/.claude/scripts/validate-epic.sh
~/.claude/scripts/epic-paths.sh
$(expanduser "~/.claude/...")  # Python
```

❌ **Bad** (Hardcoded):

```bash
/Users/kit/.claude/scripts/...
/home/alice/.claude/scripts/...
```

## Verified Compatibility

### Path Resolution

- All scripts use `$HOME` or `~` for user directory
- All Python code uses `os.path.expanduser("~")`
- No absolute paths to specific user directories

### Shell Compatibility

- Scripts use `#!/usr/bin/env bash` for portability
- Compatible with Bash 3.2+ (macOS) and 4.0+ (Linux)
- No bashisms that require specific versions

### Python Compatibility

- Requires Python 3.8+ (specified in pyproject.toml)
- Uses only standard library for path operations
- Compatible with CPython, PyPy

## Platform-Specific Notes

### macOS

- Default Bash 3.2 is supported
- Use Homebrew Python or system Python 3.8+
- May need to add `~/.local/bin` to PATH

### Linux

- Works with any distribution
- Python 3.8+ usually available via package manager
- pip may install to `/usr/local/bin` depending on config

### PATH Configuration

If `buildspec` command not found after install:

```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"

# Reload shell
source ~/.bashrc  # or source ~/.zshrc
```

## Testing Portability

Run these checks on any system:

```bash
# 1. Test CLI installation
make test

# 2. Verify symlinks
ls -la ~/.claude/commands/

# 3. Test script paths
~/.claude/scripts/validate-epic.sh --help

# 4. Check Python imports
python3 -c "from cli.app import app; print('OK')"
```

## Migration Between Machines

### Export from old machine

```bash
# No export needed - toolkit is self-contained in git repo
cd ~/tools/buildspec
git pull  # Update to latest
```

### Install on new machine

```bash
# Clone and install
git clone https://github.com/you/buildspec.git ~/tools/buildspec
cd ~/tools/buildspec
make install

# Done! Works immediately
buildspec --help
```

## Uninstall

Works the same on any platform:

```bash
cd ~/tools/buildspec
make uninstall
```

## Troubleshooting

### Command not found

```bash
# Check pip install location
pip show buildspec-cli | grep Location

# Add to PATH if needed
export PATH="$HOME/.local/bin:$PATH"
```

### Symlinks broken

```bash
# Reinstall symlinks
make reinstall
```

### Scripts not executable

```bash
# Scripts should be executable after install
# If not, run:
chmod +x ~/.claude/scripts/*.sh
chmod +x ~/.claude/hooks/*.sh
```

## Summary

✅ **Zero hardcoded paths** - Uses `$HOME` and `~/` everywhere  
✅ **Shell portable** - Bash 3.2+ compatible  
✅ **Python portable** - Python 3.8+ on any platform  
✅ **Install anywhere** - Clone to any directory  
✅ **Works everywhere** - Any Unix system with Claude Code

The toolkit is **fully portable** and will work identically on any Unix-based
machine where Claude Code is installed.
