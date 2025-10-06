"""Execute epic command implementation."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from cli.core.claude import ClaudeRunner
from cli.core.context import ProjectContext
from cli.core.prompts import PromptBuilder

console = Console()


def command(
    epic_file: Path = typer.Argument(
        ..., exists=True, file_okay=True, dir_okay=False, help="Path to epic YAML file"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show execution plan without running"
    ),
    no_parallel: bool = typer.Option(
        False, "--no-parallel", "-s", help="Execute tickets sequentially"
    ),
    project_dir: Optional[Path] = typer.Option(
        None, "--project-dir", "-p", help="Project directory (default: auto-detect)"
    ),
):
    """Execute entire epic with dependency management."""
    try:
        # Initialize context
        context = ProjectContext(cwd=project_dir)

        # Print context info
        console.print(f"[dim]Project root: {context.project_root}[/dim]")
        console.print(f"[dim]Claude dir: {context.claude_dir}[/dim]")

        # Resolve epic file path
        epic_file_resolved = context.resolve_path(str(epic_file))

        # Build prompt
        builder = PromptBuilder(context)
        prompt = builder.build_execute_epic(
            epic_file=str(epic_file_resolved), dry_run=dry_run, no_parallel=no_parallel
        )

        # Print execution mode
        mode = "DRY-RUN" if dry_run else "EXECUTING"
        style = "sequential" if no_parallel else "optimized"
        console.print(f"\n[bold]{mode}:[/bold] {epic_file} ({style})")

        # Execute
        runner = ClaudeRunner(context)
        exit_code = runner.execute(prompt)

        if exit_code == 0:
            console.print("\n[green]✓ Epic execution completed[/green]")
        else:
            raise typer.Exit(code=exit_code)

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {e}")
        raise typer.Exit(code=1) from e
