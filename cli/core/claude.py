"""Claude CLI execution wrapper."""

import subprocess
import uuid
from typing import Optional, Tuple

from rich.console import Console

from cli.core.context import ProjectContext


class ClaudeRunner:
    """Executes Claude CLI in correct project context.

    Runs Claude Code CLI as subprocess with prompts in the invocation directory.
    """

    def __init__(self, context: ProjectContext):
        """Initialize Claude CLI runner with project context for correct execution
        directory.

        Args:
            context: ProjectContext with cwd for working directory
        """
        self.context = context

    def execute(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        console: Optional[Console] = None,
        agents: Optional[str] = None,
    ) -> Tuple[int, str]:
        """Execute Claude CLI subprocess with constructed prompt in project context
        working directory.

        Args:
            prompt: Complete prompt string to pass to Claude CLI
            session_id: Optional session ID to use (generated if not provided)
            console: Optional Rich console for displaying progress spinner
            agents: Optional JSON string defining custom agents (e.g., '{"reviewer": {...}}')

        Returns:
            Tuple of (exit_code, session_id):
                - exit_code: Exit code from Claude CLI subprocess (0 = success, non-zero = failure)
                - session_id: Claude session ID used for the execution

        Raises:
            RuntimeError: If Claude CLI not found in PATH
        """
        if session_id is None:
            session_id = str(uuid.uuid4())

        try:
            # Build command args
            cmd = [
                "claude",
                "--dangerously-skip-permissions",
                "--session-id",
                session_id,
            ]

            # Add agents if provided (expects JSON string)
            if agents:
                cmd.extend(["--agents", agents])

            # Build subprocess kwargs
            run_kwargs = {
                "input": prompt,
                "cwd": self.context.cwd,
                "check": False,
                "text": True,
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
            }

            # Run subprocess (with optional spinner)
            if console:
                with console.status(
                    "[bold cyan]Executing with Claude...[/bold cyan]",
                    spinner="bouncingBar",
                ):
                    result = subprocess.run(cmd, **run_kwargs)
            else:
                result = subprocess.run(cmd, **run_kwargs)

            return result.returncode, session_id
        except FileNotFoundError as e:
            raise RuntimeError(
                "Claude CLI not found in PATH.\n"
                "Install Claude Code first: https://claude.com/claude-code"
            ) from e
