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
        from pathlib import Path

        command_file = self.context.claude_dir / "commands" / "create-epic.md"

        # Calculate output path if not provided
        if output:
            output_spec = output
        else:
            # Auto-generate: same directory as spec, with .epic.yaml extension
            spec_path = Path(planning_doc)
            epic_name = spec_path.stem.replace("-spec", "").replace("_spec", "")
            output_spec = str(spec_path.parent / f"{epic_name}.epic.yaml")

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

CRITICAL FILE NAMING REQUIREMENT:
The epic filename MUST end with .epic.yaml (not just .yaml)
Examples:
  ✓ CORRECT: progress-ui.epic.yaml
  ✓ CORRECT: user-auth.epic.yaml
  ✗ WRONG: progress-ui.yaml (missing .epic)
  ✗ WRONG: user-auth.yaml (missing .epic)

The filename must be: [epic-name].epic.yaml
Double-check the filename before creating the file!

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
        self, epic_file: str, dry_run: bool = False, no_parallel: bool = False, session_id: Optional[str] = None
    ) -> str:
        """Construct execute-epic prompt with command instructions and execution flags.

        Args:
            epic_file: Path to epic YAML file
            dry_run: Show execution plan without running
            no_parallel: Execute tickets sequentially instead of parallel
            session_id: Optional session ID to include in commits

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
        session_id_spec = (
            f"\nSession ID: {session_id}"
            if session_id
            else ""
        )

        ticket_command_file = self.context.claude_dir / "commands" / "execute-ticket.md"

        prompt = f"""Read {command_file} and execute the Task Agent Instructions.

Epic file: {epic_file}
Mode: {mode}
Execution style: {execution_style}{session_id_spec}

HEADLESS MODE: Execute autonomously without user interaction.
- You (root Claude) are the orchestrator
- Read the epic file and understand all tickets and dependencies
- Manage dependencies and track state
- Create PRs and finalize artifacts
- No interactive prompts or confirmations

CRITICAL: For EACH ticket execution:
- Use the Task tool to spawn a sub-agent with subagent_type: "general-purpose"
- Read {ticket_command_file} to get the Task Agent Instructions
- Pass those Task Agent Instructions directly to the sub-agent
- Provide the ticket file path and epic file path as context
- DO NOT use Bash tool to run "buildspec execute-ticket"
- DO NOT execute tickets inline in your context
- Each sub-agent IS the builder - it does the actual ticket work

Sub-agent prompt template for each ticket:
```
Read {ticket_command_file} and execute the Task Agent Instructions section.

Ticket file: [path-to-ticket.md]
Epic file: {epic_file}
Base commit: [commit-sha-from-dependency-or-HEAD]
Session ID: {session_id if session_id else '[to be provided]'}

Execute the ticket work as described in the Task Agent Instructions.
Include session_id in all commit messages.
```

COMMIT INSTRUCTION:
When creating git commits (in any spawned sub-agents), include the session ID in the commit message body:
session_id: {session_id if session_id else '[to be provided]'}

IMPORTANT: You are the work orchestrator. You must delegate to Task sub-agents.
Each Task sub-agent executes one ticket directly - no additional process spawning.
"""
        return prompt

    def build_execute_ticket(
        self,
        ticket_file: str,
        epic: Optional[str] = None,
        base_commit: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """Construct execute-ticket prompt with command instructions and context.

        Args:
            ticket_file: Path to ticket markdown file
            epic: Optional path to epic file for context
            base_commit: Optional base commit SHA to branch from
            session_id: Optional session ID to include in commits

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
        session_id_spec = (
            f"\nSession ID: {session_id}"
            if session_id
            else ""
        )

        prompt = f"""Read {command_file} and execute the Task Agent Instructions.

CRITICAL: You MUST use the Task tool to spawn a sub-agent for this work.
- Use Task tool with subagent_type: "general-purpose"
- Pass the Task Agent Instructions from the command file to the sub-agent
- DO NOT execute this work inline in your context
- Sub-agents preserve your context window

Ticket file: {ticket_file}{epic_context}{base_commit_spec}{session_id_spec}

HEADLESS MODE: Execute autonomously without user interaction.
- The Task agent will read the ticket file
- The Task agent will run pre-flight validation
- The Task agent will implement all requirements
- The Task agent will run tests and commit changes
- The Task agent will report completion status
- No interactive prompts or confirmations

COMMIT INSTRUCTION:
When creating git commits, include the session ID in the commit message body:
session_id: {session_id if session_id else '[to be provided]'}

IMPORTANT: You are the orchestrator. You must delegate to a Task agent using the Task
tool.
"""
        return prompt

    def build_split_epic(
        self, original_epic_path: str, spec_path: str, ticket_count: int
    ) -> str:
        """Create specialist prompt for splitting oversized epics.

        Args:
            original_epic_path: Absolute path to original epic YAML file
            spec_path: Absolute path to spec document
            ticket_count: Number of tickets in original epic

        Returns:
            Formatted prompt string for Claude subprocess

        Raises:
            FileNotFoundError: If split-epic.md command file missing
        """
        # Load the split-epic command template
        command_content = self._read_command("split-epic")

        # Build the context section
        prompt = f"""Read the split-epic command instructions and execute the Task Agent Instructions.

CONTEXT:
Original epic path: {original_epic_path}
Spec document path: {spec_path}
Ticket count: {ticket_count}
Soft limit: 12 tickets per epic (ideal)
Hard limit: 15 tickets per epic (maximum)

{command_content}

Execute the split-epic analysis and creation process as described in the Task Agent Instructions.
"""
        return prompt
