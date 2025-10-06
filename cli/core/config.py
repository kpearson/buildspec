"""XDG-compliant configuration management for buildspec."""

import os
import sys
from pathlib import Path
from typing import Optional

# Use tomllib for Python 3.11+, tomli for earlier versions
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


class Config:
    """Manages buildspec configuration following XDG Base Directory spec.

    Attributes:
        config_dir: Path to ~/.config/buildspec/
        config_file: Path to ~/.config/buildspec/config.toml
    """

    def __init__(self):
        """Initialize config paths using XDG Base Directory specification."""
        # Use XDG_CONFIG_HOME if set, otherwise default to ~/.config
        xdg_config = os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        self.config_dir = Path(xdg_config) / "buildspec"
        self.config_file = self.config_dir / "config.toml"

        # Load config if exists
        self._config = self._load() if self.config_file.exists() else {}

    def exists(self) -> bool:
        """Check if config file exists."""
        return self.config_file.exists()

    def _load(self) -> dict:
        """Load configuration from TOML file."""
        if tomllib is None:
            raise RuntimeError(
                "TOML parser not available.\n"
                "Install tomli for Python < 3.11: uv pip install tomli"
            )

        try:
            with open(self.config_file, "rb") as f:
                return tomllib.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load config: {e}")

    def get(self, key: str, default=None):
        """Get configuration value by key (supports dot notation).

        Args:
            key: Configuration key (e.g., 'claude.cli_command')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    @staticmethod
    def get_default_config() -> str:
        """Return default configuration TOML template."""
        return """# Buildspec Configuration
# Location: ~/.config/buildspec/config.toml
# Follows XDG Base Directory Specification

[claude]
# Claude CLI command (override if using custom path)
cli_command = "claude"

# Additional CLI flags (optional)
# cli_flags = ["--verbose"]

[paths]
# Claude directory location (auto-detected by default)
# claude_dir = "~/.claude"

# Default templates directory (optional)
# templates_dir = "~/.config/buildspec/templates"

[epic]
# Default epic file extension
epic_extension = ".epic.yaml"

# Rollback on failure by default
rollback_on_failure = true

[tickets]
# Default ticket directory name (relative to epic location)
tickets_dir = "tickets"

# Ticket file extension
ticket_extension = ".md"

[validation]
# Run pre-flight validation before epic execution
pre_flight_checks = true

# Require clean git working directory
require_clean_git = false

[git]
# Default branch prefix for epics
epic_branch_prefix = "epic/"

# Default branch prefix for tickets
ticket_branch_prefix = "ticket/"

# Auto-push branches to remote
auto_push = true

[github]
# Create PRs automatically
auto_create_prs = true

# PR template (optional)
# pr_template = "~/.config/buildspec/templates/pr-template.md"
"""

    def create_default(self) -> Path:
        """Create default configuration file.

        Returns:
            Path to created config file

        Raises:
            FileExistsError: If config already exists
        """
        if self.config_file.exists():
            raise FileExistsError(
                f"Configuration already exists: {self.config_file}\n"
                "Remove it first or use --force to overwrite"
            )

        # Create config directory
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Write default config
        self.config_file.write_text(self.get_default_config())

        return self.config_file

    def create_directories(self):
        """Create additional XDG directories for buildspec."""
        # Config dir (for templates, etc.)
        templates_dir = self.config_dir / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)

        # State dir (for future use - logs, history)
        xdg_state = os.getenv("XDG_STATE_HOME", os.path.expanduser("~/.local/state"))
        state_dir = Path(xdg_state) / "buildspec"
        state_dir.mkdir(parents=True, exist_ok=True)

        # Cache dir (for future use)
        xdg_cache = os.getenv("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
        cache_dir = Path(xdg_cache) / "buildspec"
        cache_dir.mkdir(parents=True, exist_ok=True)

        return {
            "config": self.config_dir,
            "templates": templates_dir,
            "state": state_dir,
            "cache": cache_dir,
        }
