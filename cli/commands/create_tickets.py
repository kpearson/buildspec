"""Create tickets command implementation."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from cli.core.claude import ClaudeRunner
from cli.core.context import ProjectContext
from cli.core.prompts import PromptBuilder

console = Console()


def command(
    epic_file: str = typer.Argument(
        ..., help="Path to epic YAML file"
    ),
    output_dir: Optional[Path] = typer.Option(
        None, "--output-dir", "-d", help="Override default tickets directory"
    ),
    project_dir: Optional[Path] = typer.Option(
        None, "--project-dir", "-p", help="Project directory (default: auto-detect)"
    ),
):
    """Create ticket files from epic definition."""
    try:
        # Strip line number notation (e.g., "file.yaml:123")
        if ":" in epic_file:
            epic_file = epic_file.split(":", 1)[0]
        
        epic_file_path = Path(epic_file)
        if not epic_file_path.exists():
            console.print(f"[red]ERROR:[/red] File not found: {epic_file}")
            raise typer.Exit(code=1)
        if not epic_file_path.is_file():
            console.print(f"[red]ERROR:[/red] Not a file: {epic_file}")
            raise typer.Exit(code=1)
        
        # Initialize context
        context = ProjectContext(cwd=project_dir)

        # Print context info
        console.print(f"[dim]Project root: {context.project_root}[/dim]")
        console.print(f"[dim]Claude dir: {context.claude_dir}[/dim]")

        # Resolve epic file path
        epic_file_resolved = context.resolve_path(epic_file)

        # Build prompt
        builder = PromptBuilder(context)
        prompt = builder.build_create_tickets(
            epic_file=str(epic_file_resolved),
            output_dir=str(output_dir) if output_dir else None,
        )

        # Print action
        console.print(f"\n[bold]Creating tickets from:[/bold] {epic_file_path}")

        # Execute
        runner = ClaudeRunner(context)
        exit_code = runner.execute(prompt)

        if exit_code == 0:
            console.print("\n[green]✓ Tickets created successfully[/green]")
        else:
            raise typer.Exit(code=exit_code)

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {e}")
        raise typer.Exit(code=1) from e
