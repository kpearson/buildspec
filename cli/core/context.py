"""Project context detection and path resolution."""

from pathlib import Path
from typing import Optional


class ProjectContext:
    """Detects project structure and provides path resolution.

    Attributes:
        cwd: Current working directory (invocation location)
        project_root: Project root directory containing .git or .claude/
        claude_dir: .claude directory (local or global)
    """

    def __init__(self, cwd: Optional[Path] = None):
        """Initialize context by detecting project root and .claude directory from cwd.

        Args:
            cwd: Working directory to start detection from (default: Path.cwd())

        Raises:
            FileNotFoundError: If .claude directory not found locally or globally
        """
        self.cwd = cwd or Path.cwd()
        self.project_root = self._find_project_root()
        self.claude_dir = self._find_claude_dir()

    def _find_project_root(self) -> Path:
        """Walk up directory tree to find project root containing .git or .claude/.

        Returns:
            Path to project root, or self.cwd if no markers found
        """
        current = self.cwd
        while current != current.parent:
            if (current / ".git").exists() or (current / ".claude").is_dir():
                return current
            current = current.parent
        return self.cwd

    def _find_claude_dir(self) -> Path:
        """Locate .claude directory, preferring local project over global ~/.claude fallback.

        Returns:
            Path to .claude directory

        Raises:
            FileNotFoundError: If .claude not found in project tree or ~/.claude
        """
        # Walk up from cwd to find local .claude/
        current = self.cwd
        while current != current.parent:
            claude_dir = current / ".claude"
            if claude_dir.is_dir():
                return claude_dir
            current = current.parent

        # Check global fallback
        global_claude = Path.home() / ".claude"
        if global_claude.is_dir():
            return global_claude

        # Not found anywhere
        raise FileNotFoundError(
            f".claude directory not found.\n"
            f"Searched from: {self.cwd}\n"
            f"Also checked: {global_claude}\n"
            f"Create .claude/ in your project or run: mkdir ~/.claude"
        )

    def resolve_path(self, path: str) -> Path:
        """Convert user-provided path to absolute path relative to invocation directory.

        Args:
            path: User-provided path (absolute or relative)

        Returns:
            Absolute resolved path
        """
        resolved = Path(path)

        if resolved.is_absolute():
            return resolved

        # Relative to invocation directory
        return (self.cwd / resolved).resolve()
