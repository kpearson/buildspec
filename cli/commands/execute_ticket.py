"""Execute ticket command implementation."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from cli.core.claude import ClaudeRunner
from cli.core.context import ProjectContext
from cli.core.prompts import PromptBuilder
from cli.utils.path_resolver import PathResolutionError, resolve_file_argument

console = Console()


def command(
    ticket_file: str = typer.Argument(
        ..., help="Path to ticket markdown file"
    ),
    epic: Optional[str] = typer.Option(
        None, "--epic", "-e", help="Path to epic file for context (or directory containing epic file)"
    ),
    base_commit: Optional[str] = typer.Option(
        None, "--base-commit", "-b", help="Base commit SHA to branch from"
    ),
    project_dir: Optional[Path] = typer.Option(
        None, "--project-dir", "-p", help="Project directory (default: auto-detect)"
    ),
):
    """Execute individual ticket."""
    try:
        # Resolve ticket file path with smart handling
        try:
            ticket_file_path = resolve_file_argument(ticket_file, arg_name="ticket file")
        except PathResolutionError as e:
            console.print(f"[red]ERROR:[/red] {e}")
            raise typer.Exit(code=1) from e
        
        # Resolve epic path if provided
        epic_path = None
        if epic:
            try:
                epic_path = resolve_file_argument(epic, expected_pattern="epic", arg_name="epic file")
            except PathResolutionError as e:
                console.print(f"[red]ERROR:[/red] {e}")
                raise typer.Exit(code=1) from e
        # Initialize context
        context = ProjectContext(cwd=project_dir)

        # Print context info
        console.print(f"[dim]Project root: {context.project_root}[/dim]")
        console.print(f"[dim]Claude dir: {context.claude_dir}[/dim]")

        # Resolve paths
        ticket_file_resolved = context.resolve_path(str(ticket_file_path))
        epic_resolved = str(context.resolve_path(str(epic_path))) if epic_path else None

        # Generate session ID
        import uuid
        session_id = str(uuid.uuid4())

        # Build prompt
        builder = PromptBuilder(context)
        prompt = builder.build_execute_ticket(
            ticket_file=str(ticket_file_resolved),
            epic=epic_resolved,
            base_commit=base_commit,
            session_id=session_id,
        )

        # Print action
        console.print(f"\n[bold]Executing ticket:[/bold] {ticket_file_path}")

        # Execute
        runner = ClaudeRunner(context)
        exit_code, returned_session_id = runner.execute(prompt, session_id=session_id, console=console)

        if exit_code == 0:
            console.print("\n[green]✓ Ticket execution completed[/green]")
            console.print(f"[dim]Session ID: {returned_session_id}[/dim]")
        else:
            raise typer.Exit(code=exit_code)

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {e}")
        raise typer.Exit(code=1) from e
