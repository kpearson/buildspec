# Buildspec Workflow Toolkit

A comprehensive Claude Code workflow automation system that transforms planning
documents into fully implemented features through autonomous agent execution.

## Installation

### Quick Start

```bash
# Clone the repository (anywhere on your system)
git clone https://github.com/you/buildspec.git ~/tools/buildspec
cd ~/tools/buildspec

# Install the toolkit
make install

# Initialize configuration (optional but recommended)
buildspec init
```

This installs:

- ✅ `buildspec` CLI command via pip (to `~/.local/bin/buildspec`)
- ✅ Claude Code files via symlinks (agents, commands, scripts to `~/.claude/`)
- ✅ All dependencies (typer, rich, tomli)

After installation, run `buildspec init` to create your configuration file at
`~/.config/buildspec/config.toml`.

### Available Make Commands

```bash
make install      # Install buildspec CLI and Claude Code files
make uninstall    # Remove buildspec CLI and Claude Code files
make reinstall    # Uninstall and reinstall buildspec
make test         # Test the CLI installation
make help         # Show available commands
```

### What Gets Installed

**CLI Binary (via pip):**

```bash
# Pip creates:
~/.local/bin/buildspec

# Points to your cloned repo (editable install)
# Changes to ~/tools/buildspec/cli/ apply instantly!
```

**Claude Code Files (via symlinks):**

```bash
~/.claude/
├── agents/           → ~/tools/buildspec/claude_files/agents/
├── commands/         → ~/tools/buildspec/claude_files/commands/
├── scripts/          → ~/tools/buildspec/claude_files/scripts/
├── hooks/            → ~/tools/buildspec/claude_files/hooks/
└── mcp-servers/      → ~/tools/buildspec/claude_files/mcp-servers/
```

## Configuration

### Initialize Configuration

```bash
# Create default configuration (XDG-compliant)
buildspec init

# Show default config without creating
buildspec init --show

# Overwrite existing config
buildspec init --force
```

This creates `~/.config/buildspec/config.toml` following the XDG Base Directory
specification. You can customize:

- Claude CLI command and flags
- Epic and ticket naming conventions
- Git branch prefixes
- Validation settings
- PR templates and more

## Usage

### CLI Commands (Headless Mode)

```bash
# Create epic from planning document
buildspec create-epic planning/my-feature-spec.md

# Generate detailed tickets (optional)
buildspec create-tickets planning/my-feature.epic.yaml

# Execute entire epic
buildspec execute-epic planning/my-feature.epic.yaml

# Execute individual tickets
buildspec execute-ticket tickets/my-ticket.md --epic planning/my-feature.epic.yaml
```

### Claude Code Commands (Interactive Mode)

```bash
# Inside Claude Code conversations:
/create-epic planning/my-feature-spec.md
/create-tickets planning/my-feature.epic.yaml
/execute-epic planning/my-feature.epic.yaml
/execute-ticket tickets/my-ticket.md --epic planning/my-feature.epic.yaml
```

Both methods work from **any directory** in **any project**!

## How It Works

### Document Transformation Pipeline

```
Planning Doc (1-2k lines) → Epic YAML (100-500 lines) → Tickets (detailed) → Implementation
     Conversation              Coordination              Execution specs      Working code
```

### Key Features

#### 🔄 **Autonomous Execution**

- Every command spawns Task agents for uninterrupted completion
- No manual intervention or permission prompts required
- Works in CI/CD environments

#### 🧠 **Context Preservation**

- Epics provide coordination context to every ticket
- Architectural decisions flow through entire implementation
- Interface contracts ensure component compatibility

#### 🔒 **Quality Assurance**

- Pre-flight test validation before any work begins
- Full test suite must pass before completion
- Git branch management with proper dependency tracking

#### 📊 **Dependency Management**

- Complex dependency graphs with sequential execution
- Stacked branch strategy for clean integration
- Automatic PR creation with proper merge ordering

### Epic Structure

Epics use YAML format with coordination requirements:

```yaml
epic: "Feature Name"
description: "What we're building"

acceptance_criteria:
  - "Measurable success criteria"

coordination_requirements:
  function_profiles: # Function signatures, arities, intents
    TicketID:
      - name: "functionName"
        arity: 2
        intent: "What it does"
        signature: "def functionName(param1, param2) -> ReturnType"

  directory_structure: # File organization
    required_paths:
      - "src/module/"
    organization_patterns:
      models: "src/models/[ModelName].py"

  integration_contracts: # What each ticket provides/consumes
    ticket-id:
      provides: ["API endpoints", "Data models"]
      consumes: ["External services"]
      interfaces: ["REST API specs"]

tickets:
  - id: ticket-name
    description: "Detailed work description"
    depends_on: []
    critical: true
```

## Project Structure

```
buildspec/
├── bin/
│   └── buildspec              # CLI entry point (direct execution)
├── cli/                       # Python CLI implementation
│   ├── __init__.py
│   ├── __main__.py
│   ├── app.py                 # Typer app + main() entry point
│   ├── commands/              # Command implementations
│   │   ├── create_epic.py
│   │   ├── create_tickets.py
│   │   ├── execute_epic.py
│   │   └── execute_ticket.py
│   ├── core/                  # Core functionality
│   │   ├── context.py         # Project context detection
│   │   ├── prompts.py         # Prompt construction
│   │   ├── claude.py          # Claude CLI execution
│   │   └── validation.py      # Pre-flight validation
│   └── utils/                 # Utilities
├── claude_files/              # Claude Code components
│   ├── agents/                # Agent definitions
│   ├── commands/              # Slash command definitions
│   ├── scripts/               # Validation scripts
│   ├── hooks/                 # Pre-execution hooks
│   └── mcp-servers/           # MCP protocol servers
├── scripts/                   # Installation and utility scripts
│   ├── install.sh             # Installation script (pip + symlinks)
│   └── uninstall.sh           # Uninstallation script
├── pyproject.toml             # Python package metadata + entry point
└── README.md                  # This file
```

## Workflow Example

```bash
# 1. Create epic from planning document
buildspec create-epic planning/user-auth-spec.md
# → Creates: planning/user-auth.epic.yaml

# 2. Execute the epic
buildspec execute-epic planning/user-auth.epic.yaml
# → Creates epic branch
# → Executes tickets sequentially with dependencies
# → Creates numbered PRs for review
# → Generates artifacts/epic-state.json
```

## Development

### Making Changes

Since the CLI is installed in editable mode (`pip install -e`), changes apply
instantly:

```bash
# Edit code
cd ~/tools/buildspec
vim cli/commands/create_epic.py

# Test immediately (no reinstall needed!)
buildspec create-epic --help  # Uses your changes
```

### Updating from Git

```bash
cd ~/tools/buildspec
git pull

# Changes available immediately (editable install)
buildspec --help  # Already using latest code
```

### Testing Direct Execution

You can also run the CLI directly without pip:

```bash
cd ~/tools/buildspec
./bin/buildspec --help  # Works without installation
```

## Requirements

- Python 3.10+
- pip (for installation)
- Claude Code CLI
- Git repository
- Bash shell

## Uninstallation

```bash
cd ~/tools/buildspec
make uninstall
```

This removes:

- CLI package via `pip uninstall buildspec-cli`
- All Claude Code files from `~/.claude/`

## Advanced Usage

### Manual Pip Install (without install-symlinks.sh)

```bash
# Install CLI only
cd ~/tools/buildspec
pip install -e .

# Manually symlink Claude Code files
ln -sf ~/tools/buildspec/claude_files/agents/*.md ~/.claude/agents/
ln -sf ~/tools/buildspec/claude_files/commands/*.md ~/.claude/commands/
# ... etc
```

### Install from GitHub (future)

```bash
# When published, install directly from GitHub
pip install git+https://github.com/you/buildspec.git

# Still need to symlink Claude Code files manually
```

## Troubleshooting

### `buildspec: command not found`

Pip installed to a directory not in your PATH. Add this to `~/.bashrc` or
`~/.zshrc`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Then reload your shell:

```bash
source ~/.bashrc  # or source ~/.zshrc
```

### Changes not applying

If you installed without `-e` (editable mode), reinstall:

```bash
cd ~/tools/buildspec
pip uninstall buildspec-cli
pip install -e .  # Note the -e flag
```

## License

MIT License - see LICENSE file for details
