"""Prompt construction for Claude CLI invocation."""

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
        """Construct create-epic prompt with command instructions and headless mode
        flags.

        Args:
            planning_doc: Path to planning document
            output: Optional output epic file path (or auto-generated)

        Returns:
            Complete prompt string for Claude CLI execution
        """
        command_file = self.context.claude_dir / "commands" / "create-epic.md"
        output_spec = output if output else "auto-generated based on planning doc name"

        prompt = f"""Read {command_file} and execute the Task Agent Instructions.

CRITICAL: You MUST use the Task tool to spawn a sub-agent for this work.
- Use Task tool with subagent_type: "general-purpose"
- Pass the Task Agent Instructions from the command file to the sub-agent
- DO NOT execute this work inline in your context
- Sub-agents preserve your context window

Planning document: {planning_doc}
Output epic file: {output_spec}

HEADLESS MODE: Execute autonomously without user interaction.
- The Task agent will read the planning document
- The Task agent will generate the epic YAML file
- The Task agent will report the created epic file path
- No interactive prompts or confirmations

IMPORTANT: You are the orchestrator. You must delegate to a Task agent using the Task
tool.
"""
        return prompt

    def build_create_tickets(
        self, epic_file: str, output_dir: Optional[str] = None
    ) -> str:
        """Construct create-tickets prompt with command instructions and output
        directory.

        Args:
            epic_file: Path to epic YAML file
            output_dir: Optional output directory for tickets (or default)

        Returns:
            Complete prompt string for Claude CLI execution
        """
        command_file = self.context.claude_dir / "commands" / "create-tickets.md"
        output_spec = (
            output_dir
            if output_dir
            else "default tickets directory based on epic location"
        )

        prompt = f"""Read {command_file} and execute the Task Agent Instructions.

CRITICAL: You MUST use the Task tool to spawn a sub-agent for this work.
- Use Task tool with subagent_type: "general-purpose"
- Pass the Task Agent Instructions from the command file to the sub-agent
- DO NOT execute this work inline in your context
- Sub-agents preserve your context window

Epic file: {epic_file}
Output directory: {output_spec}

HEADLESS MODE: Execute autonomously without user interaction.
- The Task agent will read the epic file
- The Task agent will generate all ticket markdown files
- The Task agent will report all created ticket files
- No interactive prompts or confirmations

IMPORTANT: You are the orchestrator. You must delegate to a Task agent using the Task
tool.
"""
        return prompt

    def build_execute_epic(
        self, epic_file: str, dry_run: bool = False, no_parallel: bool = False
    ) -> str:
        """Construct execute-epic prompt with command instructions and execution flags.

        Args:
            epic_file: Path to epic YAML file
            dry_run: Show execution plan without running
            no_parallel: Execute tickets sequentially instead of parallel

        Returns:
            Complete prompt string for Claude CLI execution
        """
        command_file = self.context.claude_dir / "commands" / "execute-epic.md"
        mode = (
            "DRY-RUN: Show execution plan only, do not execute tickets"
            if dry_run
            else "EXECUTE: Run all tickets"
        )
        execution_style = (
            "SEQUENTIAL: Execute tickets one at a time"
            if no_parallel
            else "OPTIMIZED: Execute with dependency-aware orchestration"
        )

        prompt = f"""Read {command_file} and execute the Task Agent Instructions.

CRITICAL: For EACH ticket execution:
- Use the Task tool to spawn a sub-agent
- Pass ticket path to /execute-ticket command
- DO NOT execute tickets inline in your context
- Sub-agents keep your context clean

Epic file: {epic_file}
Mode: {mode}
Execution style: {execution_style}

HEADLESS MODE: Execute autonomously without user interaction.
- The orchestrator Task agent will read the epic file
- The orchestrator will spawn sub-agents for each ticket execution
- The orchestrator will manage dependencies and track state
- The orchestrator will create PRs and finalize artifacts
- No interactive prompts or confirmations

IMPORTANT: You are the work orchestrator. You are not allowed to execute the tickets
yourself. You must delegate ticket execution to sub-agents.
"""
        return prompt

    def build_execute_ticket(
        self,
        ticket_file: str,
        epic: Optional[str] = None,
        base_commit: Optional[str] = None,
    ) -> str:
        """Construct execute-ticket prompt with command instructions and context.

        Args:
            ticket_file: Path to ticket markdown file
            epic: Optional path to epic file for context
            base_commit: Optional base commit SHA to branch from

        Returns:
            Complete prompt string for Claude CLI execution
        """
        command_file = self.context.claude_dir / "commands" / "execute-ticket.md"
        epic_context = f"\nEpic context: {epic}" if epic else ""
        base_commit_spec = (
            f"\nBase commit: {base_commit}"
            if base_commit
            else "\nBase commit: current HEAD"
        )

        prompt = f"""Read {command_file} and execute the Task Agent Instructions.

CRITICAL: You MUST use the Task tool to spawn a sub-agent for this work.
- Use Task tool with subagent_type: "general-purpose"
- Pass the Task Agent Instructions from the command file to the sub-agent
- DO NOT execute this work inline in your context
- Sub-agents preserve your context window

Ticket file: {ticket_file}{epic_context}{base_commit_spec}

HEADLESS MODE: Execute autonomously without user interaction.
- The Task agent will read the ticket file
- The Task agent will run pre-flight validation
- The Task agent will implement all requirements
- The Task agent will run tests and commit changes
- The Task agent will report completion status
- No interactive prompts or confirmations

IMPORTANT: You are the orchestrator. You must delegate to a Task agent using the Task
tool.
"""
        return prompt
