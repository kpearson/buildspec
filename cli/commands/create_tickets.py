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
            "[yellow]⚠ Review artifact not found, skipping review feedback[/yellow]"
        )
        return None

    # Post-process: Add session IDs to YAML frontmatter
    _add_session_ids_to_review(
        review_artifact, builder_session_id, review_session_id
    )

    console.print(f"[green]✓ Review complete: {review_artifact}[/green]")
    return str(review_artifact)


def command(
    epic_file: str = typer.Argument(
        ..., help="Path to epic YAML file (or directory containing epic file)"
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
        exit_code, session_id = runner.execute(prompt, console=console)

        if exit_code == 0:
            console.print("\n[green]✓ Tickets created successfully[/green]")
            console.print(f"[dim]Session ID: {session_id}[/dim]")

            # Invoke epic review workflow
            try:
                review_artifact = invoke_epic_review(
                    epic_file_path, session_id, context
                )

                if review_artifact:
                    console.print(f"[dim]Review saved to: {review_artifact}[/dim]")
            except Exception as e:
                console.print(
                    f"[yellow]Warning: Could not complete epic review: {e}[/yellow]"
                )
                # Continue - don't fail ticket creation on review error
        else:
            raise typer.Exit(code=exit_code)

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {e}")
        raise typer.Exit(code=1) from e
