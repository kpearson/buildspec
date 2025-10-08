# CLI Blueprint: Python CLI Development Guide

A comprehensive guide for building production-ready Python CLI applications
using modern tooling and best practices.

---

## Table of Contents

1. [Tech Stack](#tech-stack)
2. [Project Structure](#project-structure)
3. [Package Management](#package-management)
4. [Python Version Management](#python-version-management)
5. [Virtual Environment Setup](#virtual-environment-setup)
6. [Configuration Templates](#configuration-templates)
7. [Development Workflow](#development-workflow)
8. [Distribution](#distribution)

---

## Tech Stack

### Core Dependencies

| Package    | Version | Purpose                                            |
| ---------- | ------- | -------------------------------------------------- |
| **Python** | 3.8+    | Runtime (3.8 for compatibility, 3.11+ recommended) |
| **uv**     | latest  | Fast package manager (replaces pip)                |
| **Typer**  | 0.9.0+  | CLI framework with type hints                      |
| **Rich**   | 13.0.0+ | Terminal formatting and UI                         |
| **tomli**  | 2.0.0+  | TOML parser (Python < 3.11)                        |

### Optional Dependencies

| Package         | Purpose                  |
| --------------- | ------------------------ |
| **pytest**      | Testing framework        |
| **pytest-cov**  | Code coverage            |
| **ruff**        | Linter and formatter     |
| **PyInstaller** | Standalone binary builds |

---

## Project Structure

### Recommended Directory Layout

```
my-cli/
├── .github/                    # GitHub Actions workflows
│   └── workflows/
│       └── release.yml         # Multi-platform builds
│
├── bin/                        # Direct execution entry point (optional)
│   └── my-cli                  # #!/usr/bin/env python shebang script
│
├── cli/                        # CLI implementation (Python package)
│   ├── __init__.py             # Package marker
│   ├── __main__.py             # python -m cli entry point
│   ├── app.py                  # Typer app + main() entry point
│   │
│   ├── commands/               # Command implementations
│   │   ├── __init__.py
│   │   ├── init.py             # my-cli init
│   │   ├── build.py            # my-cli build
│   │   └── deploy.py           # my-cli deploy
│   │
│   ├── core/                   # Core business logic
│   │   ├── __init__.py
│   │   ├── config.py           # Configuration management
│   │   ├── context.py          # Context detection/resolution
│   │   └── validation.py       # Input validation
│   │
│   └── utils/                  # Utility functions
│       ├── __init__.py
│       ├── files.py
│       └── git.py
│
├── docs/                       # Documentation
│   ├── CLI_BLUEPRINT.md        # This file
│   ├── DISTRIBUTION.md         # Distribution strategy
│   └── ROADMAP.md              # Feature roadmap
│
├── scripts/                    # Installation/utility scripts
│   ├── install.sh              # Install CLI + setup
│   └── uninstall.sh            # Clean uninstall
│
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── test_commands/
│   ├── test_core/
│   └── conftest.py             # Pytest fixtures
│
├── .gitignore                  # Git exclusions
├── .python-version             # Python version (for pyenv/asdf)
├── Makefile                    # Common tasks
├── pyproject.toml              # Package metadata + dependencies
├── uv.lock                     # Locked dependencies
└── README.md                   # User documentation
```

### Key Directories Explained

#### `cli/` - The Python Package

**Where CLI implementation lives.** This is the installed Python package.

```
cli/
├── app.py          # Entry point with Typer app
├── commands/       # Each command gets its own file
├── core/           # Business logic, domain models
└── utils/          # Shared utilities
```

**Rules:**

- ✅ Import from `cli.commands`, `cli.core`, etc.
- ✅ Pure Python - no CLI-specific logic in `core/`
- ✅ Reusable - `core/` can be imported by other projects
- ❌ Don't mix CLI interface with business logic

#### `bin/` - Direct Execution Scripts (Optional)

**Alternative entry point for development.** Not required if using pip install.

```bash
#!/usr/bin/env python3
# bin/my-cli

import sys
from pathlib import Path

# Add project to path for development
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from cli.app import main

if __name__ == "__main__":
    main()
```

**Usage:**

```bash
./bin/my-cli --help  # Works without installation
chmod +x bin/my-cli  # Make executable
```

#### Where App Code Lives

**Two approaches for organizing application logic:**

### Approach 1: Everything in `cli/` (Simple CLIs)

**Best for:** CLI-first projects where the CLI _is_ the application

```
my-cli/
├── cli/
│   ├── commands/       # CLI interface - argument parsing
│   ├── core/           # Application logic - domain models, business logic
│   └── utils/          # Shared utilities
```

**Use when:**

- ✅ The CLI is the only interface to your code
- ✅ No plans for API, web UI, or library usage
- ✅ Simple to medium complexity
- ✅ Example: buildspec, deployment tools, code generators

**Example:**

```python
# cli/commands/build.py - CLI interface
import typer
from cli.core.builder import Builder  # Import from same package

def command(target: str = typer.Argument(...)):
    """Build the project."""
    builder = Builder(target)
    builder.build()

# cli/core/builder.py - Application logic
class Builder:
    def __init__(self, target: str):
        self.target = target

    def build(self):
        # Business logic here
        pass
```

---

### Approach 2: Separate `cli/` and `src/` (Complex Projects)

**Best for:** Projects where CLI is one interface among many

```
my-tool/
├── src/                    # Core application logic (the library)
│   ├── __init__.py
│   ├── models/             # Domain models
│   │   ├── project.py
│   │   └── config.py
│   ├── services/           # Business logic
│   │   ├── builder.py
│   │   └── deployer.py
│   └── utils/              # Shared utilities
│       └── validators.py
│
├── cli/                    # CLI interface (thin wrapper)
│   ├── __init__.py
│   ├── app.py              # Typer app
│   └── commands/           # Commands that call src/ code
│       ├── build.py
│       └── deploy.py
│
├── api/                    # Optional: REST API (uses src/)
│   └── app.py
│
└── web/                    # Optional: Web UI (uses src/)
    └── app.py
```

**Use when:**

- ✅ Multiple interfaces: CLI + API + Web UI
- ✅ Want to publish core logic as a library (importable by others)
- ✅ CLI is a thin wrapper around business logic
- ✅ Complex domain logic that other projects might reuse
- ✅ Example: AWS CLI, Docker CLI, Kubernetes kubectl

**Example:**

```python
# src/services/builder.py - Core business logic (reusable library)
class Builder:
    """Build service - can be used by CLI, API, or other code."""

    def __init__(self, target: str):
        self.target = target

    def build(self):
        # Complex business logic
        pass

# cli/commands/build.py - CLI interface (thin wrapper)
import typer
from src.services.builder import Builder  # Import from separate package

def command(target: str = typer.Argument(...)):
    """Build the project."""
    builder = Builder(target)
    builder.build()

# api/routes/build.py - API could use the same logic
from fastapi import APIRouter
from src.services.builder import Builder  # Same import!

router = APIRouter()

@router.post("/build")
def build_endpoint(target: str):
    builder = Builder(target)
    builder.build()
    return {"status": "success"}
```

**Package configuration for src/ approach:**

```toml
# pyproject.toml
[project]
name = "my-tool"

[project.scripts]
my-tool = "cli.app:main"  # CLI entry point

[tool.hatch.build.targets.wheel]
packages = ["src", "cli"]  # Install both packages

# Users can also import src as a library:
# from src.services.builder import Builder
```

---

### Comparison

| Aspect          | `cli/` Only              | `cli/` + `src/`              |
| --------------- | ------------------------ | ---------------------------- |
| **Simplicity**  | Simple                   | More structure               |
| **Reusability** | CLI-only                 | Multiple interfaces          |
| **Library Use** | Not designed for it      | Yes, publish `src/`          |
| **Imports**     | `from cli.core import X` | `from src.services import X` |
| **Best For**    | Single-purpose tools     | Multi-interface platforms    |

---

### Real-World Examples

**CLI-only approach (`cli/` contains everything):**

- **buildspec** - CLI workflow automation
- **httpie** - HTTP client CLI
- **black** - Code formatter CLI

```
buildspec/
└── cli/
    ├── commands/  # CLI commands
    └── core/      # Business logic (context, prompts, etc.)
```

**Library + CLI approach (`src/` + `cli/`):**

- **aws-cli** - Wraps boto3 library
- **docker** - Wraps Docker SDK
- **ansible** - CLI wraps ansible core library

```
aws-cli/
├── src/           # Core AWS SDK (boto3)
└── cli/           # CLI wrapper
```

---

### Recommendation

**Start with Approach 1** (`cli/` only):

```
my-cli/
└── cli/
    ├── commands/  # CLI interface
    └── core/      # Application logic
```

**Migrate to Approach 2** (`src/` + `cli/`) when you:

- Add a second interface (API, web UI)
- Want others to import your code as a library
- Have complex domain logic worth separating

**For buildspec:** We use Approach 1 because it's CLI-first with no plans for
other interfaces.

---

## Package Management

### Why uv?

**uv is 10-100x faster than pip:**

- Written in Rust
- Parallel downloads
- Better dependency resolution
- Drop-in pip replacement

### Installation

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via Homebrew
brew install uv

# Or via pip (ironic but works)
pip install uv
```

### Common Commands

```bash
# Install dependencies
uv pip install -e .              # Editable install (development)
uv pip install -e ".[dev]"       # Include dev dependencies

# Add dependency
uv add typer                     # Add to dependencies
uv add --dev pytest              # Add to dev dependencies

# Sync dependencies (from uv.lock)
uv sync                          # Install exact versions from lock

# Update dependencies
uv lock --upgrade                # Update lock file
uv sync                          # Apply updates

# Remove dependency
uv remove typer

# Run command in virtual environment
uv run pytest                    # Runs in auto-created venv
uv run python script.py
```

### Dependency Groups

**Organize dependencies by purpose:**

```toml
# pyproject.toml
[project]
dependencies = [
    "typer>=0.9.0",
    "rich>=13.0.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.13.0",
]

build = [
    "pyinstaller>=6.0.0",
]

docs = [
    "mkdocs>=1.5.0",
    "mkdocs-material>=9.0.0",
]
```

**Install specific groups:**

```bash
uv pip install -e ".[dev]"           # Install dev dependencies
uv pip install -e ".[dev,build]"     # Multiple groups
```

---

## Python Version Management

### Recommended: asdf or pyenv

**asdf (recommended - manages multiple tools):**

```bash
# Install asdf
brew install asdf

# Add Python plugin
asdf plugin add python

# Install Python version
asdf install python 3.11.7

# Set project Python version
cd my-cli
asdf local python 3.11.7  # Creates .tool-versions
```

**pyenv (Python-specific):**

```bash
# Install pyenv
brew install pyenv

# Install Python version
pyenv install 3.11.7

# Set project Python version
cd my-cli
pyenv local 3.11.7  # Creates .python-version
```

### Version Specification

**`.tool-versions` (asdf):**

```
python 3.11.7
nodejs 20.10.0
```

**`.python-version` (pyenv):**

```
3.11.7
```

**`pyproject.toml` (package requirement):**

```toml
[project]
requires-python = ">=3.8"  # Minimum version for users
```

### Choosing a Python Version

**For development:**

- **3.11+**: Recommended (faster, better errors, TOML built-in)
- **3.8**: Minimum if you need broad compatibility

**For users:**

- Set `requires-python = ">=3.8"` for compatibility
- Standalone binary (PyInstaller) removes Python dependency entirely

---

## Virtual Environment Setup

### Option 1: uv (Automatic)

**uv creates virtual environments automatically:**

```bash
# uv run auto-creates and uses venv
uv run pytest           # Creates .venv/ if needed
uv run python script.py

# Manual venv creation
uv venv                 # Creates .venv/
source .venv/bin/activate
```

### Option 2: Manual venv

```bash
# Create virtual environment
python -m venv .venv

# Activate
source .venv/bin/activate   # macOS/Linux
.venv\Scripts\activate      # Windows

# Install package
pip install -e .

# Deactivate
deactivate
```

### Best Practices

**Always use virtual environments:**

```bash
# ✅ Good - isolated environment
cd my-cli
uv venv
source .venv/bin/activate
uv pip install -e .

# ❌ Bad - pollutes system Python
sudo pip install -e .
```

**Add to `.gitignore`:**

```
# .gitignore
.venv/
venv/
__pycache__/
*.pyc
```

**Verify isolation:**

```bash
which python      # Should point to .venv/bin/python
pip list          # Should only show project dependencies
```

---

## Configuration Templates

### `pyproject.toml` - Complete Template

```toml
[project]
name = "my-cli"
version = "0.1.0"
description = "My awesome CLI tool"
readme = "README.md"
authors = [
    {name = "Your Name", email = "you@example.com"}
]
requires-python = ">=3.8"
license = {text = "MIT"}
keywords = ["cli", "automation", "tool"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

# Runtime dependencies
dependencies = [
    "typer>=0.9.0",
    "rich>=13.0.0",
    "tomli>=2.0.0 ; python_full_version < '3.11'",
]

# Entry point - creates `my-cli` command
[project.scripts]
my-cli = "cli.app:main"

# Optional entry points
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=5.0.0",
    "pytest-mock>=3.14.0",
    "ruff>=0.13.0",
]
build = [
    "pyinstaller>=6.0.0",
]

# Build system
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["cli"]

# Dependency groups (uv-specific)
[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=5.0.0",
    "pytest-mock>=3.14.0",
    "ruff>=0.13.0",
]
build = [
    "pyinstaller>=6.0.0",
]

# Ruff configuration
[tool.ruff]
line-length = 88
target-version = "py38"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
]
ignore = [
    "B008",  # Allow function calls in argument defaults (Typer pattern)
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

# Pytest configuration
[tool.pytest.ini_options]
minversion = "8.0"
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--strict-markers",
    "--tb=short",
    "--cov=cli",
    "--cov-report=term-missing",
    "--cov-report=html:htmlcov",
]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "slow: Slow running tests",
]
pythonpath = ["."]

# Coverage configuration
[tool.coverage.run]
source = ["cli"]
omit = [
    "*/tests/*",
    "*/__pycache__/*",
    "*/.venv/*",
    "*/__init__.py",
]
branch = true

[tool.coverage.report]
precision = 2
show_missing = true
skip_covered = false
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if TYPE_CHECKING:",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
```

### `cli/app.py` - Entry Point Template

```python
"""Main Typer application instance."""

import typer
from cli.commands import init, build, deploy

# Create Typer app
app = typer.Typer(
    name="my-cli",
    help="My awesome CLI tool - does amazing things",
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)

# Register commands
app.command(name="init")(init.command)
app.command(name="build")(build.command)
app.command(name="deploy")(deploy.command)


def main():
    """Entry point for pip-installed command."""
    app()


if __name__ == "__main__":
    main()
```

### `cli/__main__.py` - Module Entry Point

```python
"""Allow running as: python -m cli"""

from cli.app import main

if __name__ == "__main__":
    main()
```

### `cli/commands/init.py` - Command Template

```python
"""Init command implementation."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from cli.core.config import Config

console = Console()


def command(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing configuration"
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory (default: current directory)"
    ),
):
    """Initialize configuration in the current directory."""
    try:
        # Resolve output directory
        output_dir = output_dir or Path.cwd()

        # Business logic
        config = Config()
        config_path = config.initialize(output_dir, force=force)

        # Success output
        console.print(f"[green]✓[/green] Configuration created: {config_path}")
        console.print("\nNext steps:")
        console.print("  1. Edit configuration: [bold]my-cli config edit[/bold]")
        console.print("  2. Build project: [bold]my-cli build[/bold]")

    except FileExistsError as e:
        console.print(f"[red]ERROR:[/red] {e}")
        console.print("Use [bold]--force[/bold] to overwrite")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]ERROR:[/red] {e}")
        raise typer.Exit(code=1)
```

### `Makefile` - Common Tasks

```makefile
.PHONY: install dev test lint format clean help

help:
	@echo "My CLI - Makefile Commands"
	@echo ""
	@echo "Usage:"
	@echo "  make install      Install CLI in editable mode"
	@echo "  make dev          Install with dev dependencies"
	@echo "  make test         Run test suite"
	@echo "  make lint         Run linter"
	@echo "  make format       Format code"
	@echo "  make clean        Remove build artifacts"
	@echo "  make build        Build standalone binary"
	@echo ""

install:
	@echo "Installing CLI..."
	@uv pip install -e .
	@echo "✅ Installation complete"
	@echo "Try: my-cli --help"

dev:
	@echo "Installing with dev dependencies..."
	@uv pip install -e .
	@uv sync --group dev
	@echo "✅ Dev environment ready"

test:
	@echo "Running tests..."
	@uv run pytest

lint:
	@echo "Running linter..."
	@uv run ruff check cli/

format:
	@echo "Formatting code..."
	@uv run ruff format cli/

clean:
	@echo "Cleaning build artifacts..."
	@rm -rf build dist *.egg-info
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleaned"

build:
	@echo "Building standalone binary..."
	@uv pip install -e .
	@uv pip install pyinstaller
	@pyinstaller my-cli.spec --clean --noconfirm
	@echo "✅ Binary: dist/my-cli"
```

### `.gitignore` - Standard Exclusions

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Virtual environments
.venv/
venv/
ENV/
env/

# Distribution / packaging
build/
dist/
*.egg-info/
*.egg

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Project-specific
*.log
.env
config.local.toml
```

---

## Development Workflow

### Initial Setup

```bash
# 1. Clone/create project
git clone https://github.com/you/my-cli.git
cd my-cli

# 2. Set Python version
asdf local python 3.11.7

# 3. Create virtual environment
uv venv

# 4. Install in editable mode with dev dependencies
uv pip install -e .
uv sync --group dev

# 5. Verify installation
my-cli --help
```

### Daily Development

```bash
# Activate venv (if using manual venv)
source .venv/bin/activate

# Run CLI during development
my-cli init
my-cli build --verbose

# Run tests
make test
# or: uv run pytest

# Lint and format
make lint
make format

# Add new dependency
uv add requests
uv lock  # Update lock file

# Commit changes
git add .
git commit -m "Add feature X"
```

### Adding a New Command

**1. Create command file:**

```bash
touch cli/commands/new_command.py
```

**2. Implement command:**

```python
# cli/commands/new_command.py
import typer
from rich.console import Console

console = Console()

def command(
    arg: str = typer.Argument(..., help="Required argument"),
):
    """New command description."""
    console.print(f"Running new command with: {arg}")
```

**3. Register in app:**

```python
# cli/app.py
from cli.commands import init, build, new_command

app.command(name="new-command")(new_command.command)
```

**4. Test:**

```bash
my-cli new-command test
```

### Testing

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_commands/test_init.py

# Run with coverage
uv run pytest --cov=cli --cov-report=html

# Run only unit tests
uv run pytest -m unit

# Watch mode (requires pytest-watch)
uv run ptw
```

### Linting and Formatting

```bash
# Check code
uv run ruff check cli/

# Fix auto-fixable issues
uv run ruff check cli/ --fix

# Format code
uv run ruff format cli/

# Check specific file
uv run ruff check cli/app.py
```

---

## Distribution

### Understanding Installation Modes

There are **two fundamentally different ways** to install and distribute your
CLI:

#### Mode 1: Editable Install (Development)

**What it is:**

- Links your source code directory to Python's site-packages
- Changes to source code apply immediately (no reinstall needed)
- Python interpreter reads `.py` files every time CLI runs

**How it works:**

```bash
uv pip install -e .

# Creates:
# ~/.local/bin/my-cli -> Python script that imports cli.app:main
# Python looks up cli.app in: /path/to/your/project/cli/app.py
```

**The installed command looks like:**

```python
#!/usr/bin/python3
# ~/.local/bin/my-cli (created by pip)
import sys
from cli.app import main
sys.exit(main())
```

**Pros:**

- ✅ Instant updates - edit code, run CLI immediately
- ✅ Easy debugging - can add breakpoints, print statements
- ✅ Small footprint - just creates a small wrapper script
- ✅ Uses project Python environment

**Cons:**

- ❌ Requires Python installed on target system
- ❌ Requires all dependencies installed
- ❌ Slower startup (imports Python modules each run)
- ❌ Breaks if project directory moves/deleted
- ❌ Version conflicts with other Python projects
- ❌ Can't use in projects with different Python versions (asdf/mise conflicts)

**Use for:**

- ✅ Development and testing
- ✅ Internal tools where Python is already available
- ✅ When you need to frequently modify the CLI

---

#### Mode 2: Standalone Binary (Production)

**What it is:**

- Self-contained executable with embedded Python interpreter
- All dependencies bundled inside single file
- No external Python required

**How it works:**

```bash
pyinstaller my-cli.spec --clean --noconfirm

# Creates:
# dist/my-cli (8-15MB binary)
# Contains: Python interpreter + stdlib + dependencies + your code
```

**The binary structure:**

```
my-cli binary
├── Embedded Python 3.x runtime
├── Standard library modules
├── Dependencies (typer, rich, etc.)
└── Your cli/ package code
    ├── app.py
    ├── commands/
    └── core/
```

**Pros:**

- ✅ No Python dependency for users
- ✅ No version conflicts - isolated from system Python
- ✅ Works in ANY project (Python 2.7, 3.x, Node.js, Go, etc.)
- ✅ Faster startup (pre-compiled/cached)
- ✅ Single file distribution
- ✅ No asdf/mise/pyenv warnings
- ✅ True portability

**Cons:**

- ❌ Larger file size (8-15MB vs. ~2KB wrapper script)
- ❌ Must rebuild for each platform (macOS ARM/Intel, Linux x86_64/ARM)
- ❌ Changes require rebuild (1-2 min build time)
- ❌ Harder to debug (code is bundled)

**Use for:**

- ✅ End users who don't have Python
- ✅ Production deployments
- ✅ Cross-project tools (works in any codebase)
- ✅ Distribution via GitHub Releases, Homebrew, etc.
- ✅ Avoiding Python version conflicts

---

### Comparison Table

| Aspect                   | Editable Install              | Standalone Binary    |
| ------------------------ | ----------------------------- | -------------------- |
| **Python Required**      | Yes (3.8+)                    | No (embedded)        |
| **File Size**            | ~2KB script                   | 8-15MB binary        |
| **Startup Time**         | ~100-200ms                    | ~50-100ms            |
| **Updates**              | Instant (git pull)            | Rebuild required     |
| **Distribution**         | Git clone + pip               | Single file download |
| **Cross-Platform**       | Requires Python on target     | Build per platform   |
| **Version Conflicts**    | Yes (shared Python)           | No (isolated)        |
| **Works in Any Project** | No (Python version conflicts) | Yes (no dependency)  |
| **Debugging**            | Easy (source available)       | Hard (bundled)       |
| **Best For**             | Development                   | Production           |

---

### When to Use Each Mode

**Editable Install - Development Workflow:**

```bash
# 1. Clone repo
git clone https://github.com/you/my-cli.git
cd my-cli

# 2. Install in editable mode
uv pip install -e .

# 3. Edit code
vim cli/commands/build.py

# 4. Test immediately (no rebuild)
my-cli build --help  # Uses latest code!

# 5. Git pull updates
git pull origin main
my-cli --help  # Automatically uses new code!
```

**Standalone Binary - User Installation:**

```bash
# Download pre-built binary (no build step)
curl -L https://github.com/you/my-cli/releases/latest/download/my-cli-darwin-arm64 \
  -o ~/.local/bin/my-cli

chmod +x ~/.local/bin/my-cli

# Works immediately (no Python needed)
my-cli --help
```

---

### Recommended Strategy

**For your project:**

1. **Development**: Use editable install

   ```bash
   uv pip install -e .
   ```

2. **Distribution**: Provide both options
   - **Developers**: Install from Git with `pip install -e`
   - **Users**: Download standalone binary from GitHub Releases

3. **CI/CD**: Build binaries automatically with GitHub Actions
   ```yaml
   # .github/workflows/release.yml
   - Build binaries for macOS ARM/Intel, Linux
   - Upload to GitHub Release
   - Users download with one command
   ```

**buildspec uses this exact strategy:**

- Developers: `git clone` + `uv pip install -e .`
- Users: `curl install.sh | bash` (downloads binary)

---

### Option 1: Pip Install (Development/Internal)

**For developers and internal teams:**

```bash
# Install from local directory
pip install -e /path/to/my-cli

# Install from Git
pip install git+https://github.com/you/my-cli.git

# Install specific version
pip install git+https://github.com/you/my-cli.git@v1.0.0
```

### Option 2: Standalone Binary (Recommended for Users)

**Build self-contained executable:**

```bash
# Install PyInstaller
uv add --group build pyinstaller

# Create spec file (if not exists)
pyi-makespec cli/app.py --name my-cli --onefile

# Build binary
pyinstaller my-cli.spec --clean --noconfirm

# Test binary
./dist/my-cli --help

# Distribute
cp dist/my-cli ~/.local/bin/
```

**Benefits:**

- ✅ No Python dependency for users
- ✅ Single file distribution
- ✅ Works on any system (build per platform)
- ✅ Faster startup than Python

### Option 3: PyPI (Public Distribution)

**Publish to Python Package Index:**

```bash
# Build package
python -m build

# Upload to PyPI
python -m twine upload dist/*

# Users install with:
pip install my-cli
```

### Option 4: One-Command Install Script

**Create `install.sh` for curl-based installation:**

```bash
#!/bin/bash
# Usage: curl -sSL https://example.com/install.sh | bash

REPO="you/my-cli"
VERSION="${MY_CLI_VERSION:-latest}"

# Detect platform
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

# Download binary from GitHub Releases
curl -L "https://github.com/${REPO}/releases/download/${VERSION}/my-cli-${OS}-${ARCH}" \
  -o ~/.local/bin/my-cli

chmod +x ~/.local/bin/my-cli

echo "✅ my-cli installed successfully!"
echo "Try: my-cli --help"
```

---

## Quick Start Checklist

**Setting up a new CLI project:**

- [ ] Create project structure (`cli/`, `tests/`, `docs/`)
- [ ] Create `pyproject.toml` with dependencies and entry point
- [ ] Set Python version (`.tool-versions` or `.python-version`)
- [ ] Initialize git repository
- [ ] Create virtual environment (`uv venv`)
- [ ] Install in editable mode (`uv pip install -e .`)
- [ ] Create `cli/app.py` with Typer app
- [ ] Add first command in `cli/commands/`
- [ ] Test CLI works (`my-cli --help`)
- [ ] Add tests in `tests/`
- [ ] Configure linter/formatter (Ruff)
- [ ] Create `Makefile` for common tasks
- [ ] Write README with installation and usage
- [ ] Set up CI/CD (GitHub Actions)

**You're ready to build!** 🚀

---

## Common Patterns

### Configuration Management

```python
# cli/core/config.py
from pathlib import Path
import sys

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

class Config:
    def __init__(self):
        # XDG-compliant config location
        config_home = Path.home() / ".config" / "my-cli"
        self.config_file = config_home / "config.toml"
        self._config = self._load() if self.config_file.exists() else {}

    def _load(self):
        with open(self.config_file, "rb") as f:
            return tomllib.load(f)

    def get(self, key: str, default=None):
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
```

### Project Context Detection

```python
# cli/core/context.py
from pathlib import Path

class ProjectContext:
    def __init__(self, cwd=None):
        self.cwd = cwd or Path.cwd()
        self.project_root = self._find_project_root()

    def _find_project_root(self):
        """Walk up to find .git or config marker."""
        current = self.cwd
        while current != current.parent:
            if (current / ".git").exists():
                return current
            if (current / "my-cli.toml").exists():
                return current
            current = current.parent
        return self.cwd
```

### Rich Output Formatting

```python
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

# Simple output
console.print("[green]✓[/green] Success!")
console.print("[red]✗[/red] Error occurred")

# Table
table = Table(title="Build Results")
table.add_column("File", style="cyan")
table.add_column("Status", style="green")
table.add_row("main.py", "✓ Compiled")
console.print(table)

# Panel
console.print(Panel(
    "[bold]Configuration created![/bold]\n\nNext steps:\n  1. Edit config\n  2. Run build",
    title="Success",
    border_style="green"
))
```

---

## Troubleshooting

### `my-cli: command not found`

**Solution:** Add `~/.local/bin` to PATH

```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"

# Reload shell
source ~/.bashrc
```

### Import errors after installation

**Problem:** `ModuleNotFoundError: No module named 'cli'`

**Solution:** Ensure editable install

```bash
# Reinstall in editable mode
pip uninstall my-cli
uv pip install -e .
```

### Virtual environment issues

**Problem:** Wrong Python version or packages

**Solution:** Recreate venv

```bash
rm -rf .venv
uv venv
source .venv/bin/activate
uv pip install -e .
```

### Dependency conflicts

**Problem:** `Incompatible dependencies`

**Solution:** Update lock file

```bash
uv lock --upgrade
uv sync
```

---

## Resources

- **Typer Documentation**: https://typer.tiangolo.com/
- **Rich Documentation**: https://rich.readthedocs.io/
- **uv Documentation**: https://github.com/astral-sh/uv
- **PyInstaller**: https://pyinstaller.org/
- **Python Packaging**: https://packaging.python.org/

---

## Example CLIs Using This Blueprint

- **buildspec** - Epic-driven development automation
- **httpie** - HTTP client for the API era
- **aws-cli** - Amazon Web Services command line
- **poetry** - Python dependency management

This blueprint provides a solid foundation for building production-ready Python
CLIs! 🚀
