"""Claude CLI execution wrapper."""

import subprocess

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

    def execute(self, prompt: str) -> int:
        """Execute Claude CLI subprocess with constructed prompt in project context
        working directory.

        Args:
            prompt: Complete prompt string to pass to Claude CLI

        Returns:
            Exit code from Claude CLI subprocess (0 = success, non-zero = failure)

        Raises:
            RuntimeError: If Claude CLI not found in PATH
        """
        try:
            result = subprocess.run(
                ["claude", "-p", prompt, "--dangerously-skip-permissions"],
                cwd=self.context.cwd,
                check=False,
                text=True,
            )
            return result.returncode
        except FileNotFoundError as e:
            raise RuntimeError(
                "Claude CLI not found in PATH.\n"
                "Install Claude Code first: https://claude.com/claude-code"
            ) from e
