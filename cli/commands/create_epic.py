"""Create epic command implementation."""

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
    planning_doc: str = typer.Argument(
        ...,
        help="Path to planning document (or directory containing spec file)",
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
        # Resolve planning doc path with smart handling
        try:
            planning_doc_path = resolve_file_argument(planning_doc, expected_pattern="spec", arg_name="planning document")
        except PathResolutionError as e:
            console.print(f"[red]ERROR:[/red] {e}")
            raise typer.Exit(code=1) from e

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
        exit_code, session_id = runner.execute(prompt, console=console)

        if exit_code == 0:
            # Post-execution: find and validate epic filename
            epic_dir = planning_doc_path.parent
            expected_base = planning_doc_path.stem.replace('-spec', '').replace('_spec', '')
            
            # Look for any YAML files created
            yaml_files = sorted(epic_dir.glob('*.yaml'), key=lambda p: p.stat().st_mtime, reverse=True)
            
            for yaml_file in yaml_files:
                # Skip if already correctly named
                if yaml_file.name.endswith('.epic.yaml'):
                    continue
                    
                # Check if this looks like our epic (has the expected base name)
                if expected_base in yaml_file.stem:
                    # Rename to add .epic suffix
                    correct_name = yaml_file.stem + '.epic.yaml'
                    correct_path = yaml_file.parent / correct_name
                    yaml_file.rename(correct_path)
                    console.print(f"[dim]Renamed: {yaml_file.name} → {correct_name}[/dim]")
                    break
            
            console.print("\n[green]✓ Epic created successfully[/green]")
            console.print(f"[dim]Session ID: {session_id}[/dim]")
        else:
            raise typer.Exit(code=exit_code)

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {e}")
        raise typer.Exit(code=1) from e
