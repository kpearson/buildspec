"""Prompt construction for Claude CLI invocation."""

from pathlib import Path
from typing import Optional
from cli.core.context import ProjectContext


class PromptBuilder:
    """Constructs Claude CLI prompts by reading command files and adding parameters.

    Reads command markdown files as single source of truth and builds complete
    prompts with HEADLESS mode instructions for autonomous execution.
    """

    def __init__(self, context: ProjectContext):
        """Initialize prompt builder with project context for reading command files.

        Args:
            context: ProjectContext with claude_dir for locating command files
        """
        self.context = context

    def _read_command(self, command: str) -> str:
        """Read command markdown file from detected .claude/commands/ directory.

        Args:
            command: Command name (e.g., "create-epic", "execute-ticket")

        Returns:
            Command markdown content as string

        Raises:
            FileNotFoundError: If command file not found with helpful message
        """
        command_file = self.context.claude_dir / "commands" / f"{command}.md"

        if not command_file.exists():
            raise FileNotFoundError(
                f"Command file not found: {command_file}\n"
                f"Searched in: {self.context.claude_dir / 'commands'}\n"
                f"Available commands should be in .claude/commands/ directory"
            )

        return command_file.read_text()

    def build_create_epic(self, planning_doc: str, output: Optional[str] = None) -> str:
        """Construct create-epic prompt with command instructions and headless mode flags.

        Args:
            planning_doc: Path to planning document
            output: Optional output epic file path (or auto-generated)

        Returns:
            Complete prompt string for Claude CLI execution
        """
        command_instructions = self._read_command("create-epic")

        output_spec = output if output else "auto-generated based on planning doc name"

        prompt = f"""{command_instructions}

HEADLESS MODE: Execute autonomously without user interaction.
- Read planning document: {planning_doc}
- Generate epic file at: {output_spec}
- Report created epic file path when complete
- No interactive prompts or confirmations
"""
        return prompt

    def build_create_tickets(self, epic_file: str, output_dir: Optional[str] = None) -> str:
        """Construct create-tickets prompt with command instructions and output directory.

        Args:
            epic_file: Path to epic YAML file
            output_dir: Optional output directory for tickets (or default)

        Returns:
            Complete prompt string for Claude CLI execution
        """
        command_instructions = self._read_command("create-tickets")

        output_spec = output_dir if output_dir else "default tickets directory based on epic location"

        prompt = f"""{command_instructions}

HEADLESS MODE: Execute autonomously without user interaction.
- Read epic file: {epic_file}
- Generate all tickets in: {output_spec}
- Create one markdown file per ticket
- Report all created ticket files when complete
- No interactive prompts or confirmations
"""
        return prompt

    def build_execute_epic(self, epic_file: str, dry_run: bool = False, no_parallel: bool = False) -> str:
        """Construct execute-epic prompt with command instructions and execution flags.

        Args:
            epic_file: Path to epic YAML file
            dry_run: Show execution plan without running
            no_parallel: Execute tickets sequentially instead of parallel

        Returns:
            Complete prompt string for Claude CLI execution
        """
        command_instructions = self._read_command("execute-epic")

        mode = "DRY-RUN: Show execution plan only, do not execute tickets" if dry_run else "EXECUTE: Run all tickets"
        execution_style = "SEQUENTIAL: Execute tickets one at a time" if no_parallel else "OPTIMIZED: Execute with dependency-aware orchestration"

        prompt = f"""{command_instructions}

HEADLESS MODE: Execute autonomously without user interaction.
- Read epic file: {epic_file}
- {mode}
- {execution_style}
- Spawn orchestrator agent for dependency management
- Report execution progress and results
- No interactive prompts or confirmations
"""
        return prompt

    def build_execute_ticket(self, ticket_file: str, epic: Optional[str] = None, base_commit: Optional[str] = None) -> str:
        """Construct execute-ticket prompt with command instructions and context.

        Args:
            ticket_file: Path to ticket markdown file
            epic: Optional path to epic file for context
            base_commit: Optional base commit SHA to branch from

        Returns:
            Complete prompt string for Claude CLI execution
        """
        command_instructions = self._read_command("execute-ticket")

        epic_context = f"\n- Epic context: {epic}" if epic else ""
        base_commit_spec = f"\n- Base commit: {base_commit}" if base_commit else "\n- Base commit: current HEAD"

        prompt = f"""{command_instructions}

HEADLESS MODE: Execute autonomously without user interaction.
- Read ticket file: {ticket_file}{epic_context}{base_commit_spec}
- Spawn task agent for implementation
- Validate, implement, and test all requirements
- Report completion status and artifacts
- No interactive prompts or confirmations
"""
        return prompt
