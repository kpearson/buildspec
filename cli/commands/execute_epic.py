"""Execute epic command implementation.

This module provides the CLI command for executing epics using the state machine.
"""

from pathlib import Path
from typing import Optional, Tuple

import typer
import yaml
from rich.console import Console

from cli.epic.git_operations import GitError
from cli.epic.state_machine import EpicStateMachine

console = Console()


class StateTransitionError(Exception):
    """Exception raised when a state transition fails."""

    pass


def validate_epic_structure(epic_file_path: Path) -> Tuple[bool, Optional[str]]:
    """Validate epic YAML structure and required files.

    Args:
        epic_file_path: Path to the epic YAML file

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is None.
    """
    epic_dir = epic_file_path.parent

    # Read and parse epic YAML
    try:
        with open(epic_file_path, "r") as f:
            epic_config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return False, f"Invalid YAML syntax: {e}"
    except Exception as e:
        return False, f"Failed to read epic file: {e}"

    # Check for required "tickets" key (can be at top level or nested under "epic")
    tickets = None
    config_location = "at top level"

    if "tickets" in epic_config:
        tickets = epic_config.get("tickets")
    elif "epic" in epic_config and isinstance(epic_config["epic"], dict):
        config_location = "under 'epic:' key"
        if "tickets" in epic_config["epic"]:
            tickets = epic_config["epic"].get("tickets")
        elif "tasks" in epic_config["epic"]:
            return False, (
                "Epic YAML uses 'tasks:' key but should use 'tickets:' key. "
                "Please rename 'tasks:' to 'tickets:' under the 'epic:' section."
            )

    if tickets is None:
        # Check if user used "tasks" instead at top level
        if "tasks" in epic_config:
            return False, (
                "Epic YAML uses 'tasks:' key but should use 'tickets:' key. "
                "Please rename 'tasks:' to 'tickets:' in the epic file."
            )
        return False, f"Epic YAML missing required 'tickets:' key {config_location}"
    if not isinstance(tickets, list):
        return False, f"Epic 'tickets:' must be a list, got {type(tickets).__name__}"

    # Check if tickets list is empty
    if len(tickets) == 0:
        return False, "Epic 'tickets:' list is empty - no tickets to execute"

    # Check for tickets directory
    tickets_dir = epic_dir / "tickets"
    if not tickets_dir.exists():
        return False, (
            f"Tickets directory not found at {tickets_dir}. "
            "Epic directory must contain a 'tickets/' subdirectory."
        )

    if not tickets_dir.is_dir():
        return False, f"Expected 'tickets/' to be a directory but found a file: {tickets_dir}"

    return True, None


def command(
    epic_file: str = typer.Argument(
        ...,
        help="Path to epic YAML file",
    ),
    resume: bool = typer.Option(
        False,
        "--resume",
        help="Resume epic execution from saved state",
    ),
):
    """Execute an epic using the state machine.

    This command instantiates the EpicStateMachine and executes the epic
    autonomously, displaying progress and results.
    """
    try:
        # Convert to Path
        epic_file_path = Path(epic_file)

        # Validate epic file
        if not epic_file_path.exists():
            console.print(f"[red]ERROR:[/red] Epic file not found: {epic_file_path}")
            raise typer.Exit(code=1)

        if not epic_file_path.is_file():
            console.print(f"[red]ERROR:[/red] Path is not a file: {epic_file_path}")
            raise typer.Exit(code=1)

        if not str(epic_file_path).endswith(".epic.yaml"):
            console.print(
                f"[red]ERROR:[/red] Epic file must have .epic.yaml extension: {epic_file_path}"
            )
            console.print(
                "[yellow]Hint:[/yellow] Epic files should be named like 'my-epic.epic.yaml'"
            )
            raise typer.Exit(code=1)

        # Validate epic structure and schema
        is_valid, error_message = validate_epic_structure(epic_file_path)
        if not is_valid:
            console.print(f"[red]ERROR:[/red] Invalid epic structure: {error_message}")
            console.print(
                "[yellow]Hint:[/yellow] Check that the epic YAML has a 'tickets:' key and the tickets/ directory exists"
            )
            raise typer.Exit(code=1)

        # Display execution start
        console.print(f"\n[bold]Executing Epic:[/bold] {epic_file_path.name}")
        if resume:
            console.print("[yellow]Resuming from saved state...[/yellow]")

        # Create state machine
        try:
            state_machine = EpicStateMachine(epic_file_path, resume=resume)
        except FileNotFoundError as e:
            console.print(f"[red]ERROR:[/red] {e}")
            console.print(
                "[yellow]Hint:[/yellow] Use --resume only when resuming an interrupted epic"
            )
            raise typer.Exit(code=1)
        except ValueError as e:
            console.print(f"[red]ERROR:[/red] Invalid epic file: {e}")
            console.print(
                "[yellow]Hint:[/yellow] Check that the epic YAML file is properly formatted"
            )
            raise typer.Exit(code=1)

        # Display initial state
        console.print(f"[dim]Epic ID: {state_machine.epic_id}[/dim]")
        console.print(f"[dim]Epic branch: {state_machine.epic_branch}[/dim]")
        console.print(f"[dim]Baseline commit: {state_machine.baseline_commit[:8]}[/dim]")
        console.print(f"[dim]Total tickets: {len(state_machine.tickets)}[/dim]\n")

        # Execute the state machine
        console.print("[bold cyan]Starting epic execution...[/bold cyan]\n")

        try:
            state_machine.execute()
        except StateTransitionError as e:
            console.print(f"\n[red]State transition error:[/red] {e}")
            console.print(
                "[yellow]Hint:[/yellow] Check the state file and ensure all tickets are in valid states"
            )
            raise typer.Exit(code=1)
        except GitError as e:
            console.print(f"\n[red]Git error:[/red] {e}")
            console.print(
                "[yellow]Hint:[/yellow] Check git repository state and ensure no conflicts exist"
            )
            raise typer.Exit(code=1)

        # Display completion summary
        console.print("\n[bold]Execution Summary:[/bold]")

        completed_count = sum(
            1 for t in state_machine.tickets.values() if t.state.value == "COMPLETED"
        )
        failed_count = sum(
            1 for t in state_machine.tickets.values() if t.state.value == "FAILED"
        )
        blocked_count = sum(
            1 for t in state_machine.tickets.values() if t.state.value == "BLOCKED"
        )

        console.print(f"  ✓ Completed: [green]{completed_count}[/green]")
        if failed_count > 0:
            console.print(f"  ✗ Failed: [red]{failed_count}[/red]")
        if blocked_count > 0:
            console.print(f"  ⊘ Blocked: [yellow]{blocked_count}[/yellow]")

        console.print(f"\n[dim]Epic state: {state_machine.epic_state.value}[/dim]")

        # Determine exit code based on epic state
        if state_machine.epic_state.value == "FINALIZED":
            console.print("\n[green]✓ Epic execution completed successfully[/green]")
        elif state_machine.epic_state.value == "FAILED":
            console.print("\n[red]✗ Epic execution failed[/red]")
            console.print(
                "[yellow]Hint:[/yellow] Check failed tickets and their error messages"
            )
            raise typer.Exit(code=1)
        elif state_machine.epic_state.value == "ROLLED_BACK":
            console.print("\n[yellow]⚠ Epic rolled back due to critical failure[/yellow]")
            raise typer.Exit(code=1)
        else:
            console.print(
                f"\n[yellow]⚠ Epic execution incomplete (state: {state_machine.epic_state.value})[/yellow]"
            )
            console.print(
                "[yellow]Hint:[/yellow] Use --resume to continue execution if interrupted"
            )
            raise typer.Exit(code=1)

    except typer.Exit:
        raise
    except FileNotFoundError as e:
        console.print(f"[red]ERROR:[/red] File not found: {e}")
        console.print(
            "[yellow]Hint:[/yellow] Check that the epic file path is correct"
        )
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        console.print(
            "[yellow]Hint:[/yellow] This may be a bug. Check logs for details."
        )
        raise typer.Exit(code=1)
