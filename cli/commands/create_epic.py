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
        lines = output.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("{") and "split_epics" in line:
                data = json.loads(line)
                if "split_epics" in data:
                    return data["split_epics"]

        # If no JSON found, raise error
        raise RuntimeError("Could not find split_epics JSON in specialist output")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse specialist output as JSON: {e}")


def detect_circular_dependencies(tickets: List[Dict]) -> List[Set[str]]:
    """
    Detect circular dependency groups that must stay together.

    Uses depth-first search to detect cycles in the dependency graph.

    Args:
        tickets: List of ticket dicts with 'id' and 'depends_on' fields

    Returns:
        List of sets containing ticket IDs that have circular dependencies
    """
    # Build ticket ID to dependencies mapping
    ticket_deps = {}
    for ticket in tickets:
        ticket_id = ticket.get("id", "")
        depends_on = ticket.get("depends_on", [])
        ticket_deps[ticket_id] = set(depends_on) if depends_on else set()

    # Track visited tickets and current path for cycle detection
    visited = set()
    rec_stack = set()
    circular_groups = []

    def dfs(ticket_id: str, path: List[str]) -> Optional[List[str]]:
        """DFS to detect cycles. Returns cycle if found."""
        if ticket_id in rec_stack:
            # Found a cycle - return the cycle portion
            cycle_start = path.index(ticket_id)
            return path[cycle_start:]

        if ticket_id in visited:
            return None

        visited.add(ticket_id)
        rec_stack.add(ticket_id)
        path.append(ticket_id)

        # Visit dependencies
        for dep in ticket_deps.get(ticket_id, set()):
            cycle = dfs(dep, path[:])
            if cycle:
                return cycle

        rec_stack.remove(ticket_id)
        return None

    # Check each ticket for cycles
    for ticket_id in ticket_deps.keys():
        if ticket_id not in visited:
            cycle = dfs(ticket_id, [])
            if cycle:
                circular_groups.append(set(cycle))
                logger.info(f"Detected circular dependency group: {cycle}")

    return circular_groups


def detect_long_chains(tickets: List[Dict]) -> List[List[str]]:
    """
    Detect long dependency chains that cannot be split.

    Finds the longest path from any ticket to its deepest dependency.

    Args:
        tickets: List of ticket dicts with 'id' and 'depends_on' fields

    Returns:
        List of ticket ID lists representing dependency chains (longest first)
    """
    # Build ticket ID to dependencies mapping
    ticket_deps = {}
    for ticket in tickets:
        ticket_id = ticket.get("id", "")
        depends_on = ticket.get("depends_on", [])
        ticket_deps[ticket_id] = set(depends_on) if depends_on else set()

    # Find all paths using DFS
    def find_longest_path(ticket_id: str, visited: Set[str]) -> List[str]:
        """Find longest path from this ticket."""
        if ticket_id in visited:
            # Cycle detected, return empty to avoid infinite loop
            return []

        visited = visited | {ticket_id}
        dependencies = ticket_deps.get(ticket_id, set())

        if not dependencies:
            return [ticket_id]

        # Find longest path through dependencies
        longest = []
        for dep in dependencies:
            path = find_longest_path(dep, visited)
            if len(path) > len(longest):
                longest = path

        return [ticket_id] + longest

    # Calculate longest path for each ticket
    all_paths = []
    for ticket_id in ticket_deps.keys():
        path = find_longest_path(ticket_id, set())
        if path:
            all_paths.append(path)

    # Sort by length (longest first) and deduplicate
    all_paths.sort(key=len, reverse=True)

    # Return unique long chains (>= 12 tickets is considered long)
    seen = set()
    long_chains = []
    for path in all_paths:
        path_key = tuple(path)
        if path_key not in seen and len(path) >= 12:
            long_chains.append(path)
            seen.add(path_key)
            logger.info(f"Detected long dependency chain ({len(path)} tickets): {path}")

    return long_chains


def validate_split_independence(
    split_epics: List[Dict], epic_data: Dict
) -> Tuple[bool, str]:
    """
    Validate that split epics are fully independent with no cross-epic dependencies.

    Args:
        split_epics: List of split epic data with paths
        epic_data: Original epic data containing all tickets

    Returns:
        (is_valid, error_message) tuple - error_message is empty string if valid
    """
    # Load each split epic and build ticket->epic mapping
    ticket_to_epic = {}
    split_epic_tickets = {}

    for split_epic in split_epics:
        epic_path = split_epic.get("path")
        if not epic_path or not Path(epic_path).exists():
            continue

        try:
            epic_content = parse_epic_yaml(epic_path)
            epic_name = split_epic.get("name", epic_path)
            split_epic_tickets[epic_name] = epic_content.get("tickets", [])

            # Map each ticket to its epic
            for ticket in epic_content.get("tickets", []):
                ticket_id = ticket.get("id", "")
                ticket_to_epic[ticket_id] = epic_name
        except Exception as e:
            logger.warning(f"Could not parse split epic {epic_path}: {e}")
            continue

    # Check for cross-epic dependencies
    for epic_name, tickets in split_epic_tickets.items():
        for ticket in tickets:
            ticket_id = ticket.get("id", "")
            depends_on = ticket.get("depends_on", [])

            for dep in depends_on:
                dep_epic = ticket_to_epic.get(dep)
                if dep_epic and dep_epic != epic_name:
                    error_msg = (
                        f"Cross-epic dependency found: ticket '{ticket_id}' in epic "
                        f"'{epic_name}' depends on '{dep}' in epic '{dep_epic}'"
                    )
                    logger.error(error_msg)
                    return False, error_msg

    return True, ""


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
        console.print(
            f"[yellow]Warning: {archived_path} already exists, overwriting[/yellow]"
        )

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
    total_tickets = sum(e.get("ticket_count", 0) for e in split_epics)

    console.print(
        f"\n[green]✓ Epic split into {total_epics} independent deliverables ({total_tickets} tickets total)[/green]"
    )
    console.print("\n[bold]Created split epics:[/bold]")
    for epic in split_epics:
        name = epic.get("name", "unknown")
        path = epic.get("path", "unknown")
        count = epic.get("ticket_count", 0)
        console.print(f"  • {name}: {path} ({count} tickets)")

    console.print(f"\n[dim]Original epic archived as: {archived_path}[/dim]")
    console.print(
        "\n[yellow]Execute each epic independently - no dependencies between them[/yellow]"
    )


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


def apply_review_feedback(
    review_artifact: str, epic_path: str, builder_session_id: str, context: ProjectContext
) -> None:
    """
    Resume builder Claude session to apply review feedback to epic file.

    Args:
        review_artifact: Path to epic-file-review.md artifact
        epic_path: Path to the epic YAML file to improve
        builder_session_id: Session ID of original epic builder to resume
        context: Project context for execution
    """
    console.print("\n[blue]📝 Applying review feedback...[/blue]")

    # Read review artifact
    with open(review_artifact, "r") as f:
        review_content = f.read()

    # Build feedback application prompt
    feedback_prompt = f"""You are improving an epic file based on a comprehensive review.

## Your Task

Read the epic file at: {epic_path}

Then read this review report and implement the Priority 1 and Priority 2 recommendations:

{review_content}

## What to Do

1. Read the current epic file to understand its structure
2. Identify the specific Priority 1 and Priority 2 issues mentioned in the review
3. Make **surgical edits** to fix each issue:
   - Use Edit tool for targeted changes (not Write tool for complete rewrites)
   - Keep the existing epic structure and field names
   - Only modify the specific sections that need fixing
   - Preserve all existing content that isn't being fixed

## Priority 1 Issues (Must Fix)

Focus on these critical fixes:
- Add missing function examples to ticket descriptions (Paragraph 2)
- Define missing terms (like "epic baseline") in coordination_requirements
- Add missing specifications (error handling, acceptance criteria formats)
- Fix dependency errors

## Priority 2 Issues (Should Fix)

If time permits:
- Add integration contracts to tickets
- Clarify implementation details
- Add test coverage requirements

## Important Rules

- **DO NOT rewrite the entire epic** - make targeted edits only
- **DO NOT change the epic schema** - keep existing field names (epic, description, ticket_count, etc.)
- **DO NOT change ticket IDs** - keep existing identifiers
- **DO use Edit tool** - for surgical changes to specific sections
- **DO preserve structure** - maintain YAML formatting and organization
- **DO verify changes** - read the file after each edit to confirm

## Example of Surgical Edit

Bad (complete rewrite):
```
Write entire new epic with different structure
```

Good (targeted fix):
```
Edit ticket description to add function examples in Paragraph 2:
- Old: "Implement git operations wrapper"
- New: "Implement git operations wrapper.

  Key functions:
  - create_branch(name: str, base: str) -> None: creates branch from commit
  - push_branch(name: str) -> None: pushes branch to remote"
```

Begin by reading the epic file, then make surgical edits to fix Priority 1 issues.

## CRITICAL: Document Your Changes

After making all edits, create a summary document at the path:
{Path(epic_path).parent}/artifacts/epic-file-review-updates.md

This document should contain:

```markdown
# Epic File Review Updates

**Date**: [current date]
**Epic**: [epic name]
**Review Session**: {reviewer_session_id if 'reviewer_session_id' in review_content else 'unknown'}

## Changes Applied

### Priority 1 Fixes
[List each Priority 1 issue that was fixed, with specific changes made]

### Priority 2 Fixes
[List each Priority 2 issue that was fixed, with specific changes made]

## Changes Not Applied
[List any recommended changes that were NOT applied and why]

## Summary
[1-2 sentences describing the overall improvements made to the epic]
```

Use the Write tool to create this documentation file."""

    # Execute feedback application by resuming builder session
    runner = ClaudeRunner(context)

    with console.status(
        "[bold cyan]Claude is applying review feedback...[/bold cyan]",
        spinner="bouncingBar",
    ):
        result = subprocess.run(
            [
                "claude",
                "--dangerously-skip-permissions",
                "--session-id",
                builder_session_id,
            ],
            input=feedback_prompt,
            text=True,
            cwd=context.cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    if result.returncode == 0:
        console.print("[green]✓ Review feedback applied[/green]")

        # Check if epic file was actually modified
        epic_file = Path(epic_path)
        if epic_file.exists():
            # Compare timestamps - review artifact should be older than epic file now
            review_time = Path(review_artifact).stat().st_mtime
            epic_time = epic_file.stat().st_mtime

            if epic_time > review_time:
                console.print("[dim]Epic file updated successfully[/dim]")
            else:
                console.print(
                    "[yellow]⚠ Epic file may not have been modified[/yellow]"
                )

        # Check for updates documentation
        updates_doc = Path(epic_path).parent / "artifacts" / "epic-file-review-updates.md"
        if updates_doc.exists():
            console.print(f"[dim]Updates documented: {updates_doc}[/dim]")
        else:
            console.print(
                "[yellow]⚠ No updates documentation found (epic-file-review-updates.md)[/yellow]"
            )
    else:
        console.print(
            "[yellow]⚠ Failed to apply review feedback, but epic is still usable[/yellow]"
        )


def handle_split_workflow(
    epic_path: str, spec_path: str, ticket_count: int, context: ProjectContext
) -> None:
    """
    Orchestrate complete epic split process with edge case handling.

    Args:
        epic_path: Path to original oversized epic
        spec_path: Path to spec document
        ticket_count: Number of tickets in epic
        context: Project context for prompt building

    Raises:
        RuntimeError: If split workflow fails
    """
    console.print(
        f"\n[yellow]Epic has {ticket_count} tickets (>= 13). Initiating split workflow...[/yellow]"
    )

    try:
        # 1. Parse epic to analyze dependencies
        epic_data = parse_epic_yaml(epic_path)
        tickets = epic_data.get("tickets", [])

        # 2. Detect edge cases
        logger.info(f"Analyzing {len(tickets)} tickets for edge cases...")

        # Detect circular dependencies
        circular_groups = detect_circular_dependencies(tickets)
        if circular_groups:
            console.print(
                f"[yellow]Warning: Found {len(circular_groups)} circular dependency groups. These will stay together.[/yellow]"
            )
            for i, group in enumerate(circular_groups, 1):
                logger.info(f"Circular group {i}: {group}")

        # Detect long chains
        long_chains = detect_long_chains(tickets)
        if long_chains:
            max_chain_length = max(len(chain) for chain in long_chains)
            if max_chain_length > 12:
                console.print(
                    f"[red]Error: Epic has dependency chain of {max_chain_length} tickets (>12 limit).[/red]"
                )
                console.print("[red]Cannot split while preserving dependencies.[/red]")
                console.print(
                    "[yellow]Recommendation: Review epic design to reduce coupling between tickets.[/yellow]"
                )
                logger.error(f"Long dependency chain detected: {long_chains[0]}")
                return

        # 3. Build specialist prompt with edge case context
        prompt_builder = PromptBuilder(context)
        specialist_prompt = prompt_builder.build_split_epic(
            epic_path, spec_path, ticket_count
        )

        # 4. Invoke Claude subprocess
        console.print(
            "[blue]Invoking specialist agent to analyze and split epic...[/blue]"
        )
        result = subprocess.run(
            ["claude", "--prompt", specialist_prompt],
            capture_output=True,
            text=True,
            cwd=context.project_root,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Specialist agent failed: {result.stderr}")

        # 5. Parse specialist output to get epic names
        split_epics = parse_specialist_output(result.stdout)

        if not split_epics:
            raise RuntimeError("Specialist agent did not return any split epics")

        # 6. Validate split independence
        console.print("[blue]Validating split epic independence...[/blue]")
        is_valid, error_msg = validate_split_independence(split_epics, epic_data)
        if not is_valid:
            console.print(f"[red]Error: Split validation failed: {error_msg}[/red]")
            console.print(
                "[yellow]Epic is too tightly coupled to split. Keeping as single epic.[/yellow]"
            )
            logger.error(f"Split independence validation failed: {error_msg}")
            return

        # 7. Create subdirectories
        base_dir = Path(epic_path).parent
        epic_names = [e["name"] for e in split_epics]
        created_dirs = create_split_subdirectories(str(base_dir), epic_names)

        console.print(
            f"[dim]Created {len(created_dirs)} subdirectories for split epics[/dim]"
        )

        # 8. Archive original
        archived_path = archive_original_epic(epic_path)
        console.print(f"[dim]Archived original epic to: {archived_path}[/dim]")

        # 9. Display results
        display_split_results(split_epics, archived_path)

    except Exception as e:
        console.print(f"[red]ERROR during split workflow:[/red] {e}")
        logger.exception("Split workflow failed")
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
    no_split: bool = typer.Option(
        False,
        "--no-split",
        help="Skip automatic epic splitting even if ticket count >= 13",
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
                    # Step 1: Review the epic
                    review_artifact = invoke_epic_file_review(
                        str(epic_path), session_id, context
                    )

                    # Step 2: Apply review feedback if review succeeded
                    if review_artifact:
                        apply_review_feedback(
                            review_artifact, str(epic_path), session_id, context
                        )

                    # Step 3: Validate ticket count and trigger split workflow if needed
                    epic_data = parse_epic_yaml(str(epic_path))
                    ticket_count = epic_data["ticket_count"]

                    if validate_ticket_count(ticket_count):
                        # Check if --no-split flag is set
                        if no_split:
                            console.print(
                                f"\n[yellow]Warning: --no-split flag set. Epic has {ticket_count} tickets which may be difficult to execute.[/yellow]"
                            )
                            console.print(
                                "[yellow]Recommendation: Epics with >= 13 tickets may take longer than 2 hours to execute.[/yellow]"
                            )
                            console.print(
                                "\n[green]✓ Epic created successfully[/green]"
                            )
                            console.print(f"[dim]Session ID: {session_id}[/dim]")
                        else:
                            # Trigger split workflow
                            handle_split_workflow(
                                epic_path=str(epic_path),
                                spec_path=str(planning_doc_path),
                                ticket_count=ticket_count,
                                context=context,
                            )
                    else:
                        # Normal success path
                        console.print("\n[green]✓ Epic created successfully[/green]")
                        console.print(f"[dim]Session ID: {session_id}[/dim]")
                except Exception as e:
                    console.print(
                        f"[yellow]Warning: Could not validate epic for splitting: {e}[/yellow]"
                    )
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
