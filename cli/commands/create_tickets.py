"""Create tickets command implementation."""

import logging
import re
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import typer
import yaml
from rich.console import Console
from rich.table import Table

from cli.core.claude import ClaudeRunner
from cli.core.context import ProjectContext
from cli.core.prompts import PromptBuilder
from cli.utils import ReviewTargets, apply_review_feedback
from cli.utils.path_resolver import PathResolutionError, resolve_file_argument

console = Console()
logger = logging.getLogger(__name__)


def _add_session_ids_to_review(
    review_artifact: Path, builder_session_id: str, reviewer_session_id: str
) -> None:
    """
    Add or update session IDs in the YAML frontmatter of the review artifact.

    Args:
        review_artifact: Path to epic-review.md file
        builder_session_id: Session ID of the ticket builder
        reviewer_session_id: Session ID of the epic reviewer
    """
    content = review_artifact.read_text()

    # Check if YAML frontmatter exists
    frontmatter_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)

    if frontmatter_match:
        # Parse existing frontmatter
        frontmatter = frontmatter_match.group(1)

        # Update or add session IDs
        if 'builder_session_id:' in frontmatter:
            frontmatter = re.sub(
                r'builder_session_id:.*',
                f'builder_session_id: {builder_session_id}',
                frontmatter
            )
        else:
            frontmatter += f'\nbuilder_session_id: {builder_session_id}'

        if 'reviewer_session_id:' in frontmatter:
            frontmatter = re.sub(
                r'reviewer_session_id:.*',
                f'reviewer_session_id: {reviewer_session_id}',
                frontmatter
            )
        else:
            frontmatter += f'\nreviewer_session_id: {reviewer_session_id}'

        # Reconstruct content with updated frontmatter
        body = content[frontmatter_match.end():]
        updated_content = f'---\n{frontmatter}\n---\n{body}'
    else:
        # No frontmatter exists - create it
        frontmatter = f"""---
builder_session_id: {builder_session_id}
reviewer_session_id: {reviewer_session_id}
---"""
        updated_content = f'{frontmatter}\n\n{content.lstrip()}'

    # Write updated content
    review_artifact.write_text(updated_content)
    logger.info(f"Added session IDs to epic review artifact: {review_artifact}")


def invoke_epic_review(
    epic_file_path: Path, builder_session_id: str, context: ProjectContext
) -> Optional[str]:
    """
    Invoke epic-review command on all files in the epic directory.

    Args:
        epic_file_path: Path to the epic YAML file
        builder_session_id: Session ID of the ticket builder Claude session
        context: Project context for execution

    Returns:
        Path to review artifact file, or None if review failed
    """
    console.print("\n[blue]🔍 Invoking epic review...[/blue]")

    # Ensure artifacts directory exists
    epic_dir = epic_file_path.parent
    artifacts_dir = epic_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Build epic review prompt using SlashCommand
    review_prompt = f"/epic-review {epic_file_path}"

    # Execute tickets review in new Claude session
    runner = ClaudeRunner(context)
    review_exit_code, review_session_id = runner.execute(
        review_prompt, console=console
    )

    if review_exit_code != 0:
        console.print(
            "[yellow]⚠ Epic review failed, skipping review feedback[/yellow]"
        )
        return None

    # Check for review artifact
    review_artifact = artifacts_dir / "epic-review.md"

    if not review_artifact.exists():
        console.print(
            "[yellow]⚠ Review artifact not found, "
            "skipping review feedback[/yellow]"
        )
        return None

    # Post-process: Add session IDs to YAML frontmatter
    _add_session_ids_to_review(
        review_artifact, builder_session_id, review_session_id
    )

    console.print(f"[green]✓ Review complete: {review_artifact}[/green]")
    return str(review_artifact)


def _validate_ticket_filenames(epic_file_path: Path, tickets_dir: Path) -> Tuple[bool, List[Dict]]:
    """Validate that ticket filenames match their IDs in the epic YAML.

    Args:
        epic_file_path: Path to epic YAML file
        tickets_dir: Directory where ticket files should exist

    Returns:
        (is_valid, list_of_mismatches) where each mismatch is a dict with:
            - ticket_id: Expected ID from epic
            - expected_file: Expected filename
            - found_files: List of similar files found (if any)
    """
    # Parse epic YAML to get ticket IDs
    try:
        with open(epic_file_path, "r") as f:
            epic_config = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to parse epic YAML: {e}")
        return False, [{"error": f"Failed to parse epic YAML: {e}"}]

    # Extract ticket IDs (handle both top-level and nested under "epic" key)
    tickets_data = epic_config.get("tickets")
    if tickets_data is None and "epic" in epic_config:
        if isinstance(epic_config["epic"], dict):
            tickets_data = epic_config["epic"].get("tickets", [])

    if not tickets_data:
        return True, []  # No tickets to validate

    # Check each ticket
    mismatches = []
    for ticket in tickets_data:
        ticket_id = ticket.get("id")
        if not ticket_id:
            continue

        expected_file = tickets_dir / f"{ticket_id}.md"

        if not expected_file.exists():
            # Look for similar files that might be misnamed
            similar_files = []
            for f in tickets_dir.glob("*.md"):
                # Check if filename contains parts of the ticket ID
                if any(part in f.stem for part in ticket_id.split("-")):
                    similar_files.append(f.name)

            mismatches.append({
                "ticket_id": ticket_id,
                "expected_file": f"{ticket_id}.md",
                "found_files": similar_files
            })

    return len(mismatches) == 0, mismatches


def _archive_tickets(tickets_dir: Path, artifacts_dir: Path) -> None:
    """Archive existing tickets directory to artifacts with timestamp.

    Args:
        tickets_dir: Tickets directory to archive
        artifacts_dir: Artifacts directory where archive will be placed
    """
    if not tickets_dir.exists():
        return

    # Create artifacts dir if needed
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Generate archive name with unix timestamp
    timestamp = int(time.time())
    archive_name = f"{timestamp}-tickets"
    archive_path = artifacts_dir / archive_name

    # Move tickets directory to archive
    shutil.move(str(tickets_dir), str(archive_path))
    console.print(f"[dim]Archived existing tickets → {archive_path}[/dim]")
    logger.info(f"Archived tickets directory to {archive_path}")


def _check_tickets_exist(tickets_dir: Path) -> bool:
    """Check if ticket markdown files already exist.

    Args:
        tickets_dir: Tickets directory to check

    Returns:
        True if tickets exist, False otherwise
    """
    if not tickets_dir.exists():
        return False

    ticket_files = list(tickets_dir.glob("*.md"))
    return len(ticket_files) > 0


def _check_review_completed(artifacts_dir: Path, review_filename: str) -> bool:
    """Check if review artifact exists.

    Args:
        artifacts_dir: Artifacts directory
        review_filename: Name of review file (e.g., "epic-review.md")

    Returns:
        True if review exists, False otherwise
    """
    review_path = artifacts_dir / review_filename
    return review_path.exists()


def _check_review_feedback_applied(artifacts_dir: Path, updates_filename: str) -> bool:
    """Check if review feedback was successfully applied.

    Args:
        artifacts_dir: Artifacts directory
        updates_filename: Name of updates doc (e.g., "epic-review-updates.md")

    Returns:
        True if review feedback applied successfully, False otherwise
    """
    import yaml

    updates_path = artifacts_dir / updates_filename
    if not updates_path.exists():
        return False

    try:
        content = updates_path.read_text()
        if not content.startswith("---"):
            return False

        # Parse frontmatter
        parts = content.split("---", 2)
        if len(parts) < 3:
            return False

        frontmatter = yaml.safe_load(parts[1])
        return frontmatter.get("status") == "completed"
    except Exception:
        return False


def command(
    epic_file: str = typer.Argument(
        ..., help="Path to epic YAML file (or directory containing epic file)"
    ),
    output_dir: Optional[Path] = typer.Option(
        None, "--output-dir", "-d", help="Override default tickets directory"
    ),
    project_dir: Optional[Path] = typer.Option(
        None,
        "--project-dir",
        "-p",
        help="Project directory (default: auto-detect)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force full rebuild, ignore existing artifacts (destructive)",
    ),
):
    """Create ticket files from epic definition."""
    try:
        # Resolve epic file path with smart handling
        try:
            epic_file_path = resolve_file_argument(
                epic_file, expected_pattern="epic", arg_name="epic file"
            )
        except PathResolutionError as e:
            console.print(f"[red]ERROR:[/red] {e}")
            raise typer.Exit(code=1) from e

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

        # Determine tickets directory and artifacts directory
        epic_dir = epic_file_path.parent
        tickets_dir = output_dir if output_dir else epic_dir / "tickets"
        artifacts_dir = epic_dir / "artifacts"

        # Archive existing tickets if --force flag is set
        if force and _check_tickets_exist(tickets_dir):
            _archive_tickets(tickets_dir, artifacts_dir)

        # Check for existing tickets (skip creation if they exist)
        tickets_exist = _check_tickets_exist(tickets_dir)

        if tickets_exist:
            console.print(
                f"\n[blue]Existing tickets detected in: {tickets_dir}[/blue]"
            )
            console.print("[dim]Resuming from completed steps...[/dim]")

        # Step 1: Create tickets
        session_id = None
        exit_code = None

        if not tickets_exist:
            # Print action
            console.print(f"\n[bold]Creating tickets from:[/bold] {epic_file_path}")

            # Execute
            runner = ClaudeRunner(context)
            exit_code, session_id = runner.execute(prompt, console=console)

            if exit_code != 0:
                raise typer.Exit(code=exit_code)

            console.print("[green]✓ Tickets created[/green]")

            # Validate ticket filenames match epic YAML IDs
            console.print("\n[blue]🔍 Validating ticket filenames...[/blue]")
            is_valid, mismatches = _validate_ticket_filenames(epic_file_path, tickets_dir)

            if not is_valid:
                console.print("[red]✗ Ticket filename validation failed[/red]\n")

                # Create detailed error table
                table = Table(title="Ticket Filename Mismatches", show_header=True, header_style="bold red")
                table.add_column("Ticket ID", style="cyan")
                table.add_column("Expected Filename", style="green")
                table.add_column("Similar Files Found", style="yellow")

                for mismatch in mismatches:
                    if "error" in mismatch:
                        console.print(f"[red]ERROR:[/red] {mismatch['error']}")
                        continue

                    similar = "\n".join(mismatch["found_files"]) if mismatch["found_files"] else "(none)"
                    table.add_row(
                        mismatch["ticket_id"],
                        mismatch["expected_file"],
                        similar
                    )

                console.print(table)
                console.print("\n[yellow]Fix:[/yellow] Ticket filenames must exactly match their IDs from the epic YAML.")
                console.print(f"[yellow]Hint:[/yellow] Rename files in {tickets_dir} to match expected filenames.")
                console.print("[dim]Example: mv ticket-001-data-models.md data-models-1.md[/dim]\n")

                raise typer.Exit(code=1)

            console.print("[green]✓ Ticket filenames validated[/green]")
        else:
            console.print("[green]✓ Tickets exist (skipping creation)[/green]")
            exit_code = 0  # Assume success if tickets already exist

        if exit_code == 0:
            console.print(f"[dim]Session ID: {session_id}[/dim]") if session_id else None

            # Step 2: Epic review
            try:
                review_completed = _check_review_completed(
                    artifacts_dir, "epic-review.md"
                )

                review_artifact = None
                if not review_completed:
                    review_artifact = invoke_epic_review(
                        epic_file_path, session_id, context
                    )
                else:
                    console.print(
                        "[green]✓ Epic review exists (skipping)[/green]"
                    )
                    review_artifact = str(artifacts_dir / "epic-review.md")

                if review_artifact:
                    # Step 3: Apply review feedback
                    feedback_applied = _check_review_feedback_applied(
                        artifacts_dir, "epic-review-updates.md"
                    )

                    if not feedback_applied:
                        # Apply review feedback to epic and tickets
                        try:
                            # Use the same tickets_dir that was calculated above
                            # (respects --output-dir flag)
                            epic_name = epic_dir.name

                            # Collect all ticket markdown files
                            ticket_file_paths = list(tickets_dir.glob("*.md"))

                            # Read reviewer_session_id from review artifact
                            # frontmatter
                            review_content = Path(review_artifact).read_text()
                            # Use builder session if not in frontmatter
                            reviewer_session_id = session_id if session_id else "unknown"
                            frontmatter_match = re.match(
                                r"^---\n(.*?)\n---\n", review_content, re.DOTALL
                            )
                            if frontmatter_match:
                                frontmatter = frontmatter_match.group(1)
                                reviewer_match = re.search(
                                    r"reviewer_session_id:\s*(\S+)", frontmatter
                                )
                                if reviewer_match:
                                    reviewer_session_id = reviewer_match.group(1)

                            # Create ReviewTargets for epic-review
                            targets = ReviewTargets(
                                primary_file=epic_file_path,
                                additional_files=ticket_file_paths,
                                editable_directories=[epic_dir, tickets_dir],
                                artifacts_dir=artifacts_dir,
                                updates_doc_name="epic-review-updates.md",
                                log_file_name="epic-review.log",
                                error_file_name="epic-review.error.log",
                                epic_name=epic_name,
                                reviewer_session_id=reviewer_session_id,
                                review_type="epic"
                            )

                            # Apply review feedback
                            apply_review_feedback(
                                review_artifact_path=Path(review_artifact),
                                builder_session_id=session_id if session_id else "unknown",
                                context=context,
                                targets=targets,
                                console=console
                            )
                        except Exception as e:
                            # Review feedback is optional - log warning but
                            # don't fail command
                            console.print(
                                f"[yellow]Warning: Failed to apply review "
                                f"feedback: {e}[/yellow]"
                            )
                            # Continue with command execution
                    else:
                        console.print(
                            "[green]✓ Review feedback already applied (skipping)[/green]"
                        )
            except Exception as e:
                console.print(
                    f"[yellow]Warning: Could not complete epic review: "
                    f"{e}[/yellow]"
                )
                # Continue - don't fail ticket creation on review error
        else:
            raise typer.Exit(code=exit_code)

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {e}")
        raise typer.Exit(code=1) from e
