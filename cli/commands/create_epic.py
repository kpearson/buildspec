"""Create epic command implementation."""

import logging
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
        review_artifact: Path to epic-file-review.md file
        builder_session_id: Session ID of the epic builder
        reviewer_session_id: Session ID of the epic reviewer
    """
    import re

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
        # No frontmatter exists - add it
        # Extract metadata from old format if present
        date_match = re.search(r'\*\*Date:\*\* (\S+)', content)
        epic_match = re.search(r'\*\*Epic:\*\* (.+?)(?:\*\*|$)', content)
        ticket_match = re.search(r'\*\*Ticket Count:\*\* (\d+)', content)

        date = date_match.group(1) if date_match else 'unknown'
        epic = epic_match.group(1).strip() if epic_match else 'unknown'
        ticket_count = ticket_match.group(1) if ticket_match else 'unknown'

        # Create frontmatter
        frontmatter = f"""---
date: {date}
epic: {epic}
ticket_count: {ticket_count}
builder_session_id: {builder_session_id}
reviewer_session_id: {reviewer_session_id}
---"""

        # Remove old metadata from body if present
        body = content
        if date_match or epic_match or ticket_match:
            # Remove the old metadata line(s)
            body = re.sub(
                r'\*\*Date:\*\*.*?\*\*Ticket Count:\*\* \d+\n*',
                '',
                body,
                flags=re.DOTALL
            )

        updated_content = f'{frontmatter}\n\n{body.lstrip()}'

    # Write updated content
    review_artifact.write_text(updated_content)
    logger.info(f"Added session IDs to review artifact: {review_artifact}")


def invoke_epic_file_review(
    epic_path: str, builder_session_id: str, context: ProjectContext
) -> Optional[str]:
    """
    Invoke epic-file-review command on the newly created epic YAML file.

    Args:
        epic_path: Path to the epic YAML file to review
        builder_session_id: Session ID of the epic builder Claude session
        context: Project context for execution

    Returns:
        Path to review artifact file, or None if review failed
    """
    console.print("\n[blue]🔍 Invoking epic file review...[/blue]")

    # Ensure artifacts directory exists
    artifacts_dir = Path(epic_path).parent / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Build epic file review prompt using SlashCommand
    epic_name = Path(epic_path).stem.replace(".epic", "")
    review_prompt = f"/epic-file-review {epic_path}"

    # Execute epic review in new Claude session
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
    artifacts_dir = Path(epic_path).parent / "artifacts"
    review_artifact = artifacts_dir / "epic-file-review.md"

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


def _check_epic_exists(epic_dir: Path, expected_base: str) -> Optional[Path]:
    """Check if epic YAML file already exists.

    Args:
        epic_dir: Directory to search for epic file
        expected_base: Expected base name for epic file

    Returns:
        Path to epic file if found, None otherwise
    """
    # Look for .epic.yaml files
    yaml_files = list(epic_dir.glob("*.epic.yaml"))

    for yaml_file in yaml_files:
        if expected_base in yaml_file.stem:
            return yaml_file

    return None


def _check_review_completed(artifacts_dir: Path, review_filename: str) -> bool:
    """Check if review artifact exists.

    Args:
        artifacts_dir: Artifacts directory
        review_filename: Name of review file (e.g., "epic-file-review.md")

    Returns:
        True if review exists, False otherwise
    """
    review_path = artifacts_dir / review_filename
    return review_path.exists()


def _check_review_feedback_applied(artifacts_dir: Path, updates_filename: str) -> bool:
    """Check if review feedback was successfully applied.

    Args:
        artifacts_dir: Artifacts directory
        updates_filename: Name of updates doc (e.g., "epic-file-review-updates.md")

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
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force full rebuild, ignore existing artifacts (destructive)",
    ),
):
    """Create epic file from planning document."""
    try:
        # Resolve planning doc path with smart handling
        try:
            planning_doc_path = resolve_file_argument(
                planning_doc, expected_pattern="spec", arg_name="planning document"
            )
        except PathResolutionError as e:
            console.print(f"[red]ERROR:[/red] {e}")
            raise typer.Exit(code=1) from e

        # Initialize context
        context = ProjectContext(cwd=project_dir)

        # Print context info
        console.print(f"[dim]Project root: {context.project_root}[/dim]")
        console.print(f"[dim]Claude dir: {context.claude_dir}[/dim]")

        # Resolve planning doc path (use the already-resolved path from path_resolver)
        planning_doc_resolved = context.resolve_path(str(planning_doc_path))

        # Build prompt
        builder = PromptBuilder(context)
        prompt = builder.build_create_epic(
            planning_doc=str(planning_doc_resolved),
            output=str(output) if output else None,
        )

        # Determine epic directory and expected base name
        epic_dir = planning_doc_path.parent
        expected_base = planning_doc_path.stem.replace("-spec", "").replace(
            "_spec", ""
        )
        artifacts_dir = epic_dir / "artifacts"

        # Check for existing epic (auto-resume detection)
        existing_epic = _check_epic_exists(epic_dir, expected_base)
        epic_exists = existing_epic is not None and not force

        if epic_exists:
            console.print(
                f"\n[blue]Existing epic detected: {existing_epic.name}[/blue]"
            )
            console.print("[dim]Resuming from completed steps...[/dim]")

        # Step 1: Create Epic YAML
        session_id = None
        exit_code = None

        if force or not epic_exists:
            if force and epic_exists:
                console.print(
                    "[yellow]⚠ --force flag: Rebuilding epic (existing file will be overwritten)[/yellow]"
                )

            # Print action
            console.print(f"\n[bold]Creating epic from:[/bold] {planning_doc_path}")

            # Execute
            runner = ClaudeRunner(context)
            exit_code, session_id = runner.execute(prompt, console=console)

            if exit_code != 0:
                raise typer.Exit(code=exit_code)

            console.print("[green]✓ Epic YAML created[/green]")
        else:
            console.print("[green]✓ Epic YAML exists (skipping creation)[/green]")
            exit_code = 0  # Assume success if epic already exists

        # Find epic path for subsequent steps
        if exit_code == 0:
            # Post-execution: find and validate epic filename
            epic_dir = planning_doc_path.parent
            expected_base = planning_doc_path.stem.replace("-spec", "").replace(
                "_spec", ""
            )

            # Look for any YAML files created
            yaml_files = sorted(
                epic_dir.glob("*.yaml"), key=lambda p: p.stat().st_mtime, reverse=True
            )

            epic_path = None
            for yaml_file in yaml_files:
                # Skip if already correctly named
                if yaml_file.name.endswith(".epic.yaml"):
                    epic_path = yaml_file
                    continue

                # Check if this looks like our epic (has the expected base name)
                if expected_base in yaml_file.stem:
                    # Rename to add .epic suffix
                    correct_name = yaml_file.stem + ".epic.yaml"
                    correct_path = yaml_file.parent / correct_name
                    yaml_file.rename(correct_path)
                    console.print(
                        f"[dim]Renamed: {yaml_file.name} → {correct_name}[/dim]"
                    )
                    epic_path = correct_path
                    break

            # Invoke epic review workflow
            if epic_path and epic_path.exists():
                try:
                    # Step 2: Epic file review
                    review_completed = _check_review_completed(
                        artifacts_dir, "epic-file-review.md"
                    )

                    review_artifact = None
                    if force or not review_completed:
                        if force and review_completed:
                            console.print(
                                "[yellow]⚠ --force flag: Re-running epic file review[/yellow]"
                            )

                        review_artifact = invoke_epic_file_review(
                            str(epic_path), session_id, context
                        )
                    else:
                        console.print(
                            "[green]✓ Epic file review exists (skipping)[/green]"
                        )
                        review_artifact = str(artifacts_dir / "epic-file-review.md")

                    # Step 3: Apply review feedback if review succeeded
                    if review_artifact:
                        feedback_applied = _check_review_feedback_applied(
                            artifacts_dir, "epic-file-review-updates.md"
                        )

                        if force or not feedback_applied:
                            if force and feedback_applied:
                                console.print(
                                    "[yellow]⚠ --force flag: Re-applying review feedback[/yellow]"
                                )

                            # Extract required parameters for ReviewTargets
                            import re
                            epic_file_path = Path(epic_path)
                            epic_dir = epic_file_path.parent
                            artifacts_dir = epic_dir / "artifacts"
                            epic_name = epic_file_path.stem.replace(".epic", "")

                            # Extract reviewer_session_id from review artifact
                            reviewer_session_id = "unknown"
                            try:
                                review_content = Path(review_artifact).read_text()
                                session_match = re.search(
                                    r'reviewer_session_id:\s*(\S+)',
                                    review_content
                                )
                                if session_match:
                                    reviewer_session_id = session_match.group(1)
                            except Exception:
                                pass

                            # Create ReviewTargets instance
                            targets = ReviewTargets(
                                primary_file=epic_file_path,
                                additional_files=[],
                                editable_directories=[epic_dir],
                                artifacts_dir=artifacts_dir,
                                updates_doc_name="epic-file-review-updates.md",
                                log_file_name="epic-file-review.log",
                                error_file_name="epic-file-review.error.log",
                                epic_name=epic_name,
                                reviewer_session_id=reviewer_session_id,
                                review_type="epic-file"
                            )

                            # Call shared apply_review_feedback()
                            apply_review_feedback(
                                review_artifact_path=Path(review_artifact),
                                builder_session_id=session_id,
                                context=context,
                                targets=targets,
                                console=console
                            )
                        else:
                            console.print(
                                "[green]✓ Review feedback already applied (skipping)[/green]"
                            )

                    # Success!
                    console.print("\n[green]✓ Epic created successfully[/green]")
                    console.print(f"[dim]Session ID: {session_id}[/dim]")
                except Exception as e:
                    console.print(
                        f"[yellow]Warning: Post-creation workflow error: {e}[/yellow]"
                    )
                    # Continue - don't fail epic creation on review errors
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
