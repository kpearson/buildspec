"""Create epic command implementation."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from cli.core.claude import ClaudeRunner
from cli.core.context import ProjectContext
from cli.core.prompts import PromptBuilder

console = Console()


def command(
    planning_doc: str = typer.Argument(
        ...,
        help="Path to planning document (.md file)",
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Override output epic file path"
    ),
    project_dir: Optional[Path] = typer.Option(
        None, "--project-dir", "-p", help="Project directory (default: auto-detect)"
    ),
):
    """Create epic file from planning document."""
    try:
        # Strip line number notation (e.g., "file.md:123")
        if ":" in planning_doc:
            planning_doc = planning_doc.split(":", 1)[0]
        
        planning_doc_path = Path(planning_doc)
        if not planning_doc_path.exists():
            console.print(f"[red]ERROR:[/red] File not found: {planning_doc}")
            raise typer.Exit(code=1)
        if not planning_doc_path.is_file():
            console.print(f"[red]ERROR:[/red] Not a file: {planning_doc}")
            raise typer.Exit(code=1)
        
        # Initialize context
        context = ProjectContext(cwd=project_dir)

        # Print context info
        console.print(f"[dim]Project root: {context.project_root}[/dim]")
        console.print(f"[dim]Claude dir: {context.claude_dir}[/dim]")

        # Resolve planning doc path
        planning_doc_resolved = context.resolve_path(planning_doc)

        # Build prompt
        builder = PromptBuilder(context)
        prompt = builder.build_create_epic(
            planning_doc=str(planning_doc_resolved),
            output=str(output) if output else None,
        )

        # Print action
        console.print(f"\n[bold]Creating epic from:[/bold] {planning_doc_path}")

        # Execute
        runner = ClaudeRunner(context)
        exit_code = runner.execute(prompt)

        if exit_code == 0:
            console.print("\n[green]✓ Epic created successfully[/green]")
        else:
            raise typer.Exit(code=exit_code)

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {e}")
        raise typer.Exit(code=1) from e
