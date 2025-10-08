"""Create epic command implementation."""

import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import typer
from rich.console import Console

from cli.core.claude import ClaudeRunner
from cli.core.context import ProjectContext
from cli.core.prompts import PromptBuilder
from cli.utils.epic_validator import parse_epic_yaml, validate_ticket_count
from cli.utils.path_resolver import PathResolutionError, resolve_file_argument

console = Console()
logger = logging.getLogger(__name__)


def parse_specialist_output(output: str) -> List[Dict]:
    """
    Parse specialist agent output to extract split epic information.

    Args:
        output: Specialist agent stdout containing split epic data

    Returns:
        List of dicts with 'name', 'path', 'ticket_count' for each split epic

    Raises:
        RuntimeError: If output format is invalid or unparseable
    """
    # Look for JSON output block in the specialist output
    # Expected format: {"split_epics": [{"name": "epic1", "path": "...", "ticket_count": N}, ...]}
    try:
        # Try to find JSON block in output
        lines = output.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('{') and 'split_epics' in line:
                data = json.loads(line)
                if 'split_epics' in data:
                    return data['split_epics']

        # If no JSON found, raise error
        raise RuntimeError("Could not find split_epics JSON in specialist output")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse specialist output as JSON: {e}")


def create_split_subdirectories(base_dir: str, epic_names: List[str]) -> List[str]:
    """
    Create subdirectory structure for each split epic.

    Creates the directory structure:
    [base-dir]/[epic-name]/
    [base-dir]/[epic-name]/tickets/

    Args:
        base_dir: Base directory path (e.g., .epics/user-auth/)
        epic_names: List of epic names for subdirectories

    Returns:
        List of created directory paths

    Raises:
        ValueError: If paths are outside .epics/ directory
        OSError: If directory creation fails
    """
    base_path = Path(base_dir).resolve()
    epics_root = Path(".epics").resolve()

    # Security: Validate paths are within .epics/
    if not str(base_path).startswith(str(epics_root)):
        raise ValueError(f"Path {base_path} is outside .epics/ directory")

    created_dirs = []

    for epic_name in epic_names:
        # Create epic subdirectory
        epic_dir = base_path / epic_name
        epic_dir.mkdir(parents=True, exist_ok=True)

        # Create tickets subdirectory
        tickets_dir = epic_dir / "tickets"
        tickets_dir.mkdir(exist_ok=True)

        created_dirs.append(str(epic_dir))
        console.print(f"[green]Created directory: {epic_dir}[/green]")

    return created_dirs


def archive_original_epic(epic_path: str) -> str:
    """
    Archive the original oversized epic by renaming with .original suffix.

    Args:
        epic_path: Absolute path to epic YAML file

    Returns:
        Path to archived file (.original)

    Raises:
        ValueError: If path is outside .epics/ directory
        OSError: If file operation fails
    """
    epic_file = Path(epic_path).resolve()
    epics_root = Path(".epics").resolve()

    # Security: Validate path is within .epics/
    if not str(epic_file).startswith(str(epics_root)):
        raise ValueError(f"Path {epic_file} is outside .epics/ directory")

    # Create archived filename
    archived_path = epic_file.with_suffix(epic_file.suffix + ".original")

    # Warn if .original already exists
    if archived_path.exists():
        console.print(f"[yellow]Warning: {archived_path} already exists, overwriting[/yellow]")

    # Rename file
    epic_file.rename(archived_path)
    console.print(f"[green]Archived original epic: {archived_path}[/green]")

    return str(archived_path)


def display_split_results(split_epics: List[Dict], archived_path: str) -> None:
    """
    Display clear feedback about split results.

    Args:
        split_epics: List of dicts with split epic information
        archived_path: Path to archived original epic
    """
    total_epics = len(split_epics)
    total_tickets = sum(e.get('ticket_count', 0) for e in split_epics)

    console.print(f"\n[green]✓ Epic split into {total_epics} independent deliverables ({total_tickets} tickets total)[/green]")
    console.print("\n[bold]Created split epics:[/bold]")
    for epic in split_epics:
        name = epic.get('name', 'unknown')
        path = epic.get('path', 'unknown')
        count = epic.get('ticket_count', 0)
        console.print(f"  • {name}: {path} ({count} tickets)")

    console.print(f"\n[dim]Original epic archived as: {archived_path}[/dim]")
    console.print("\n[yellow]Execute each epic independently - no dependencies between them[/yellow]")


def handle_split_workflow(epic_path: str, spec_path: str, ticket_count: int, context: ProjectContext) -> None:
    """
    Orchestrate complete epic split process.

    Args:
        epic_path: Path to original oversized epic
        spec_path: Path to spec document
        ticket_count: Number of tickets in epic
        context: Project context for prompt building

    Raises:
        RuntimeError: If split workflow fails
    """
    console.print(f"\n[yellow]Epic has {ticket_count} tickets (>= 13). Initiating split workflow...[/yellow]")

    try:
        # 1. Build specialist prompt
        prompt_builder = PromptBuilder(context)
        specialist_prompt = prompt_builder.build_split_epic(epic_path, spec_path, ticket_count)

        # 2. Invoke Claude subprocess
        console.print("[blue]Invoking specialist agent to analyze and split epic...[/blue]")
        result = subprocess.run(
            ["claude", "--prompt", specialist_prompt],
            capture_output=True,
            text=True,
            cwd=context.project_root
        )

        if result.returncode != 0:
            raise RuntimeError(f"Specialist agent failed: {result.stderr}")

        # 3. Parse specialist output to get epic names
        split_epics = parse_specialist_output(result.stdout)

        if not split_epics:
            raise RuntimeError("Specialist agent did not return any split epics")

        # 4. Create subdirectories
        base_dir = Path(epic_path).parent
        epic_names = [e['name'] for e in split_epics]
        created_dirs = create_split_subdirectories(str(base_dir), epic_names)

        console.print(f"[dim]Created {len(created_dirs)} subdirectories for split epics[/dim]")

        # 5. Archive original
        archived_path = archive_original_epic(epic_path)
        console.print(f"[dim]Archived original epic to: {archived_path}[/dim]")

        # 6. Display results
        display_split_results(split_epics, archived_path)

    except Exception as e:
        console.print(f"[red]ERROR during split workflow:[/red] {e}")
        # Re-raise to let caller handle
        raise


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

            epic_path = None
            for yaml_file in yaml_files:
                # Skip if already correctly named
                if yaml_file.name.endswith('.epic.yaml'):
                    epic_path = yaml_file
                    continue

                # Check if this looks like our epic (has the expected base name)
                if expected_base in yaml_file.stem:
                    # Rename to add .epic suffix
                    correct_name = yaml_file.stem + '.epic.yaml'
                    correct_path = yaml_file.parent / correct_name
                    yaml_file.rename(correct_path)
                    console.print(f"[dim]Renamed: {yaml_file.name} → {correct_name}[/dim]")
                    epic_path = correct_path
                    break

            # Validate ticket count and trigger split workflow if needed
            if epic_path and epic_path.exists():
                try:
                    epic_data = parse_epic_yaml(str(epic_path))
                    ticket_count = epic_data['ticket_count']

                    if validate_ticket_count(ticket_count):
                        # Trigger split workflow
                        handle_split_workflow(
                            epic_path=str(epic_path),
                            spec_path=str(planning_doc_path),
                            ticket_count=ticket_count,
                            context=context
                        )
                    else:
                        # Normal success path
                        console.print("\n[green]✓ Epic created successfully[/green]")
                        console.print(f"[dim]Session ID: {session_id}[/dim]")
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not validate epic for splitting: {e}[/yellow]")
                    # Continue - don't fail epic creation on validation error
                    console.print("\n[green]✓ Epic created successfully[/green]")
                    console.print(f"[dim]Session ID: {session_id}[/dim]")
            else:
                console.print("\n[green]✓ Epic created successfully[/green]")
                console.print(f"[dim]Session ID: {session_id}[/dim]")
        else:
            raise typer.Exit(code=exit_code)

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {e}")
        raise typer.Exit(code=1) from e
