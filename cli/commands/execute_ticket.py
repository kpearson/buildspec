"""Execute ticket command implementation."""

import typer
from pathlib import Path
from typing import Optional
from rich.console import Console

from cli.core.context import ProjectContext
from cli.core.prompts import PromptBuilder
from cli.core.claude import ClaudeRunner

console = Console()


def command(
    ticket_file: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        help="Path to ticket markdown file"
    ),
    epic: Optional[Path] = typer.Option(
        None,
        "--epic",
        help="Path to epic file for context"
    ),
    base_commit: Optional[str] = typer.Option(
        None,
        "--base-commit",
        help="Base commit SHA to branch from"
    ),
    project_dir: Optional[Path] = typer.Option(
        None,
        "--project-dir",
        help="Project directory (default: auto-detect)"
    )
):
    """Execute individual ticket."""
    try:
        # Initialize context
        context = ProjectContext(cwd=project_dir)

        # Print context info
        console.print(f"[dim]Project root: {context.project_root}[/dim]")
        console.print(f"[dim]Claude dir: {context.claude_dir}[/dim]")

        # Resolve paths
        ticket_file_resolved = context.resolve_path(str(ticket_file))
        epic_resolved = str(context.resolve_path(str(epic))) if epic else None

        # Build prompt
        builder = PromptBuilder(context)
        prompt = builder.build_execute_ticket(
            ticket_file=str(ticket_file_resolved),
            epic=epic_resolved,
            base_commit=base_commit
        )

        # Print action
        console.print(f"\n[bold]Executing ticket:[/bold] {ticket_file}")

        # Execute
        runner = ClaudeRunner(context)
        exit_code = runner.execute(prompt)

        if exit_code == 0:
            console.print("\n[green]✓ Ticket execution completed[/green]")
        else:
            raise typer.Exit(code=exit_code)

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {e}")
        raise typer.Exit(code=1)
