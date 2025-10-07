"""Execute epic command implementation."""

import re
import subprocess
import threading
import time
from pathlib import Path
from typing import List, Optional, Set

import typer
from rich.console import Console
from rich.live import Live
from rich.table import Table

from cli.core.claude import ClaudeRunner
from cli.core.context import ProjectContext
from cli.core.prompts import PromptBuilder
from cli.utils.commit_parser import extract_ticket_name
from cli.utils.path_resolver import PathResolutionError, resolve_file_argument

console = Console()


class GitWatcher:
    """Watches git commits in real-time during Claude execution."""

    def __init__(self, cwd: Path, initial_commit: Optional[str] = None):
        """Initialize git watcher.

        Args:
            cwd: Working directory to watch git commits in
            initial_commit: Initial commit SHA before execution starts
        """
        self.cwd = cwd
        self.initial_commit = initial_commit
        self.completed_tickets: Set[str] = set()
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

    def start(self):
        """Start watching git commits in background thread."""
        self.thread = threading.Thread(target=self._watch_commits, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop watching git commits."""
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)

    def _watch_commits(self):
        """Background thread that polls git log every 2 seconds."""
        while not self.stop_event.is_set():
            try:
                self._check_for_new_commits()
            except Exception:
                # Silently ignore git errors - we'll fall back to basic spinner
                pass
            time.sleep(2)

    def _check_for_new_commits(self):
        """Check git log for new commits since initial commit."""
        if not self.initial_commit:
            return

        try:
            # Get commits since initial commit
            result = subprocess.run(
                ["git", "log", f"{self.initial_commit}..HEAD", "--format=%s"],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )

            # Parse commit messages for ticket names
            commit_messages = result.stdout.strip().split("\n")
            for msg in commit_messages:
                if msg:
                    ticket_name = self._extract_ticket_name(msg)
                    if ticket_name:
                        with self.lock:
                            self.completed_tickets.add(ticket_name)

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            # Silently ignore git errors
            pass

    def _extract_ticket_name(self, commit_message: str) -> Optional[str]:
        """Extract ticket name from commit message.

        Delegates to the commit_parser utility for comprehensive parsing.

        Args:
            commit_message: Git commit message

        Returns:
            Ticket name if found, None otherwise
        """
        return extract_ticket_name(commit_message)

    def get_completed_tickets(self) -> List[str]:
        """Get list of completed tickets (thread-safe).

        Returns:
            Sorted list of completed ticket names
        """
        with self.lock:
            return sorted(self.completed_tickets)


def get_current_git_commit(cwd: Path) -> Optional[str]:
    """Get current git commit SHA.

    Args:
        cwd: Working directory

    Returns:
        Current commit SHA or None if not in git repo or error occurs
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return None


def create_status_table(completed_tickets: List[str]) -> Table:
    """Create Rich table showing completed tickets.

    Args:
        completed_tickets: List of completed ticket names

    Returns:
        Rich Table with completed tickets
    """
    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
    table.add_column("Status", style="green", width=8)
    table.add_column("Ticket", style="white")

    if not completed_tickets:
        table.add_row("⏳", "[dim]Executing with Claude...[/dim]")
    else:
        for ticket in completed_tickets:
            table.add_row("✓", ticket)

    return table


def command(
    epic_file: str = typer.Argument(
        ..., help="Path to epic YAML file (or directory containing epic file)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show execution plan without running"
    ),
    no_parallel: bool = typer.Option(
        False, "--no-parallel", "-s", help="Execute tickets sequentially"
    ),
    no_live_updates: bool = typer.Option(
        False, "--no-live-updates", help="Disable git commit watching and use basic spinner (useful in CI environments)"
    ),
    project_dir: Optional[Path] = typer.Option(
        None, "--project-dir", "-p", help="Project directory (default: auto-detect)"
    ),
):
    """Execute entire epic with dependency management."""
    try:
        # Resolve epic file path with smart handling
        try:
            epic_file_path = resolve_file_argument(epic_file, expected_pattern="epic", arg_name="epic file")
        except PathResolutionError as e:
            console.print(f"[red]ERROR:[/red] {e}")
            raise typer.Exit(code=1) from e
        # Initialize context
        context = ProjectContext(cwd=project_dir)

        # Print context info
        console.print(f"[dim]Project root: {context.project_root}[/dim]")
        console.print(f"[dim]Claude dir: {context.claude_dir}[/dim]")

        # Resolve epic file path
        epic_file_resolved = context.resolve_path(str(epic_file_path))

        # Generate session ID
        import uuid
        session_id = str(uuid.uuid4())

        # Build prompt
        builder = PromptBuilder(context)
        prompt = builder.build_execute_epic(
            epic_file=str(epic_file_resolved), dry_run=dry_run, no_parallel=no_parallel, session_id=session_id
        )

        # Print execution mode
        mode = "DRY-RUN" if dry_run else "EXECUTING"
        style = "sequential" if no_parallel else "optimized"
        console.print(f"\n[bold]{mode}:[/bold] {epic_file_path} ({style})")

        # Get initial git commit for watching
        initial_commit = get_current_git_commit(context.cwd)

        # Initialize git watcher if we're in a git repo and live updates are enabled
        git_watcher = None
        if initial_commit and not no_live_updates:
            git_watcher = GitWatcher(context.cwd, initial_commit)

        # Execute with git watching (live updates) or basic spinner
        runner = ClaudeRunner(context)

        try:
            if git_watcher:
                # Start git watcher
                git_watcher.start()

                # Run Claude subprocess in background thread
                result_container = {"exit_code": None, "session_id": None}
                exception_container = {"exception": None}

                def run_claude():
                    try:
                        exit_code, returned_session_id = runner.execute(
                            prompt, session_id=session_id, console=None
                        )
                        result_container["exit_code"] = exit_code
                        result_container["session_id"] = returned_session_id
                    except Exception as e:
                        exception_container["exception"] = e

                claude_thread = threading.Thread(target=run_claude)
                claude_thread.start()

                # Live display with git commit watching
                with Live(create_status_table([]), console=console, refresh_per_second=2) as live:
                    while claude_thread.is_alive():
                        completed_tickets = git_watcher.get_completed_tickets()
                        live.update(create_status_table(completed_tickets))
                        time.sleep(0.5)

                    # Final update
                    completed_tickets = git_watcher.get_completed_tickets()
                    live.update(create_status_table(completed_tickets))

                # Wait for thread to complete
                claude_thread.join()

                # Check for exceptions
                if exception_container["exception"]:
                    raise exception_container["exception"]

                exit_code = result_container["exit_code"]
                returned_session_id = result_container["session_id"]

            else:
                # Use basic spinner (no live updates or not in git repo)
                exit_code, returned_session_id = runner.execute(
                    prompt, session_id=session_id, console=console
                )

        finally:
            # Clean up git watcher
            if git_watcher:
                git_watcher.stop()

        if exit_code == 0:
            console.print("\n[green]✓ Epic execution completed[/green]")
            console.print(f"[dim]Session ID: {returned_session_id}[/dim]")
        else:
            raise typer.Exit(code=exit_code)

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {e}")
        raise typer.Exit(code=1) from e
