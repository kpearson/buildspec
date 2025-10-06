"""Validation utilities for file and dependency checking."""

import subprocess
from pathlib import Path


class Validator:
    """Static validation methods for pre-execution checks."""

    @staticmethod
    def validate_planning_doc(path: str) -> bool:
        """Validate planning document exists and has .md extension.

        Args:
            path: Path to planning document

        Returns:
            True if valid

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file doesn't have .md extension
        """
        file_path = Path(path)

        if not file_path.exists():
            raise FileNotFoundError(f"Planning document not found: {path}")

        if file_path.suffix != ".md":
            raise ValueError(f"Planning document must be a .md file: {path}")

        return True

    @staticmethod
    def validate_epic_file(path: str) -> bool:
        """Validate epic file exists and has .yaml or .yml extension.

        Args:
            path: Path to epic file

        Returns:
            True if valid

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file doesn't have .yaml or .yml extension
        """
        file_path = Path(path)

        if not file_path.exists():
            raise FileNotFoundError(f"Epic file not found: {path}")

        if file_path.suffix not in [".yaml", ".yml"]:
            raise ValueError(f"Epic file must be a .yaml or .yml file: {path}")

        return True

    @staticmethod
    def validate_ticket_file(path: str) -> bool:
        """Validate ticket file exists and has .md extension.

        Args:
            path: Path to ticket file

        Returns:
            True if valid

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file doesn't have .md extension
        """
        file_path = Path(path)

        if not file_path.exists():
            raise FileNotFoundError(f"Ticket file not found: {path}")

        if file_path.suffix != ".md":
            raise ValueError(f"Ticket file must be a .md file: {path}")

        return True

    @staticmethod
    def validate_claude_installed() -> bool:
        """Verify Claude CLI is installed and available in PATH.

        Returns:
            True if installed

        Raises:
            RuntimeError: If Claude CLI not found or not executable
        """
        try:
            subprocess.run(
                ["claude", "--version"], capture_output=True, check=True, timeout=5
            )
            return True
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            raise RuntimeError(
                "Claude CLI not found or not working.\n"
                "Install Claude Code first: https://claude.com/claude-code"
            ) from e
