"""Claude CLI execution wrapper."""

import subprocess
import uuid
from typing import Optional, Tuple

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

    def execute(self, prompt: str, session_id: Optional[str] = None) -> Tuple[int, str]:
        """Execute Claude CLI subprocess with constructed prompt in project context
        working directory.

        Args:
            prompt: Complete prompt string to pass to Claude CLI
            session_id: Optional session ID to use (generated if not provided)

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
            # Pipe prompt via stdin instead of -p flag to avoid subprocess hanging issues
            result = subprocess.run(
                [
                    "claude",
                    "--dangerously-skip-permissions",
                    "--session-id",
                    session_id,
                ],
                input=prompt,
                cwd=self.context.cwd,
                check=False,
                text=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            return result.returncode, session_id
        except FileNotFoundError as e:
            raise RuntimeError(
                "Claude CLI not found in PATH.\n"
                "Install Claude Code first: https://claude.com/claude-code"
            ) from e
