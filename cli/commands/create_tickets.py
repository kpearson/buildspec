"""Create tickets command implementation."""

import logging
import re
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

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

        # Check for existing tickets (auto-resume detection)
        tickets_exist = _check_tickets_exist(tickets_dir) and not force

        if tickets_exist:
            console.print(
                f"\n[blue]Existing tickets detected in: {tickets_dir}[/blue]"
            )
            console.print("[dim]Resuming from completed steps...[/dim]")

        # Step 1: Create tickets
        session_id = None
        exit_code = None

        if force or not tickets_exist:
            if force and tickets_exist:
                console.print(
                    "[yellow]⚠ --force flag: Rebuilding tickets (existing files will be overwritten)[/yellow]"
                )

            # Print action
            console.print(f"\n[bold]Creating tickets from:[/bold] {epic_file_path}")

            # Execute
            runner = ClaudeRunner(context)
            exit_code, session_id = runner.execute(prompt, console=console)

            if exit_code != 0:
                raise typer.Exit(code=exit_code)

            console.print("[green]✓ Tickets created[/green]")
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
                if force or not review_completed:
                    if force and review_completed:
                        console.print(
                            "[yellow]⚠ --force flag: Re-running epic review[/yellow]"
                        )

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

                    if force or not feedback_applied:
                        if force and feedback_applied:
                            console.print(
                                "[yellow]⚠ --force flag: Re-applying review feedback[/yellow]"
                            )

                        # Apply review feedback to epic and tickets
                        try:
                            epic_dir = epic_file_path.parent
                            tickets_dir = epic_dir / "tickets"
                            artifacts_dir = epic_dir / "artifacts"
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
