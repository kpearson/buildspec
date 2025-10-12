"""Review feedback configuration and dependency injection.

This module provides the ReviewTargets dataclass, which serves as a
dependency injection container for review feedback application workflows.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, List, Literal, Set

if TYPE_CHECKING:
    from rich.console import Console

    from cli.core.context import ProjectContext


@dataclass
class ReviewTargets:
    """Dependency injection container for review feedback configuration.

    This dataclass encapsulates all file paths, directories, and metadata
    required to apply review feedback to an epic or epic-file. It serves
    as a contract between callers (create_epic.py, create_tickets.py) and
    the review feedback application logic.

    Usage Pattern:
        Instantiate ReviewTargets with specific paths and configuration,
        then pass to apply_review_feedback() for processing. This allows
        the same review feedback logic to work for different review types
        (epic-file-review, epic-review) by varying the configuration.

    Example:
        targets = ReviewTargets(
            primary_file=Path(".epics/my-epic/my-epic.epic.yaml"),
            additional_files=[],
            editable_directories=[Path(".epics/my-epic")],
            artifacts_dir=Path(".epics/my-epic/artifacts"),
            updates_doc_name="epic-file-review-updates.md",
            log_file_name="epic-file-review.log",
            error_file_name="epic-file-review-errors.log",
            epic_name="my-epic",
            reviewer_session_id="550e8400-e29b-41d4-a716-446655440000",
            review_type="epic-file"
        )

    Fields:
        primary_file: Path to the main target file (typically epic YAML).
        additional_files: List of additional files to edit (e.g., ticket
            markdown files for epic-review).
        editable_directories: List of directories where files can be
            modified during review feedback application.
        artifacts_dir: Directory where review artifacts and logs are
            written.
        updates_doc_name: Filename for the documentation of changes made
            during review feedback application.
        log_file_name: Filename for stdout logs from the review feedback
            session.
        error_file_name: Filename for stderr logs from the review feedback
            session.
        epic_name: Name of the epic being reviewed (for documentation).
        reviewer_session_id: Session ID of the review session that
            generated the feedback.
        review_type: Type of review - "epic-file" for epic YAML only, or
            "epic" for epic YAML plus all ticket files.

    Note:
        No validation is performed in this dataclass. Validation happens
        at call sites before instantiating ReviewTargets.
    """

    primary_file: Path
    additional_files: List[Path]
    editable_directories: List[Path]
    artifacts_dir: Path
    updates_doc_name: str
    log_file_name: str
    error_file_name: str
    epic_name: str
    reviewer_session_id: str
    review_type: Literal["epic-file", "epic"]


def _create_template_doc(  # noqa: E501
    targets: ReviewTargets, builder_session_id: str
) -> None:
    """Create a template documentation file before Claude runs.

    This function writes an initial template documentation file with frontmatter
    marked as "status: in_progress". The template serves as a placeholder that
    Claude is instructed to replace with actual documentation of changes made.
    If Claude fails to update the template, the in_progress status enables
    detection of the failure and triggers fallback documentation creation.

    The template includes:
    - YAML frontmatter with metadata for traceability
    - An in-progress message explaining Claude is working
    - Placeholder sections that indicate what will be documented

    Args:
        targets: ReviewTargets configuration containing file paths and
            metadata. Template is written to artifacts_dir / updates_doc_name.
        builder_session_id: Session ID of the builder command (create-epic
            or create-tickets) applying the review feedback. Used for
            traceability in logs.

    Side Effects:
        - Creates parent directories if they don't exist using Path.mkdir()
        - Writes a UTF-8 encoded markdown file with YAML frontmatter
        - Overwrites the file if it already exists

    Raises:
        OSError: If directory creation fails or file cannot be written (e.g.,
            permission denied, disk full). The error message from the OS will
            provide details about the failure.

    Frontmatter Schema:
        The template includes frontmatter with the following fields:
        - date: Current date in YYYY-MM-DD format
        - epic: Name of the epic (from targets.epic_name)
        - builder_session_id: Session ID of the builder command
        - reviewer_session_id: Session ID from targets.reviewer_session_id
        - status: Set to "in_progress" to enable failure detection

    Workflow Context:
        1. This function is called BEFORE invoking Claude
        2. Claude is instructed to replace the template with documentation
        3. After Claude runs, the frontmatter status is checked:
           - If status=completed → Claude succeeded
           - If status=in_progress → Claude failed, create fallback doc
    """
    # Create artifacts directory if it doesn't exist
    targets.artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Generate template file path
    template_path = targets.artifacts_dir / targets.updates_doc_name

    # Get current date in YYYY-MM-DD format
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Build template content with frontmatter and placeholder sections
    template_content = f"""---
date: {current_date}
epic: {targets.epic_name}
builder_session_id: {builder_session_id}
reviewer_session_id: {targets.reviewer_session_id}
status: in_progress
---

# Review Feedback Application In Progress

Review feedback is being applied...

This template will be replaced by Claude with documentation of changes made.

## Changes Applied

(This section will be populated by Claude)

## Files Modified

(This section will be populated by Claude)

## Review Feedback Addressed

(This section will be populated by Claude)
"""

    # Write template to file with UTF-8 encoding
    template_path.write_text(template_content, encoding="utf-8")


def _create_fallback_updates_doc(
    targets: ReviewTargets, stdout: str, stderr: str, builder_session_id: str
) -> None:
    """Create fallback documentation when Claude fails to update template.

    This function serves as a safety net when Claude fails to complete
    the review feedback application process. It analyzes stdout/stderr
    to extract insights, detects which files were potentially modified,
    and creates comprehensive documentation to aid manual verification.

    The fallback document includes:
    - Complete frontmatter with status (completed_with_errors or completed)
    - Analysis of what happened based on stdout/stderr
    - Full stdout and stderr logs in code blocks
    - List of files that may have been modified (detected from stdout patterns)
    - Guidance for manual verification and next steps

    Args:
        targets: ReviewTargets configuration containing file paths/metadata
        stdout: Standard output from Claude session (file operations log)
        stderr: Standard error from Claude session (errors and warnings)
        builder_session_id: Session ID of the builder session

    Side Effects:
        Writes a markdown file with frontmatter to:
        targets.artifacts_dir / targets.updates_doc_name

    Analysis Strategy:
        - Parses stdout for file modification patterns:
          * "Edited file: /path/to/file"
          * "Wrote file: /path/to/file"
          * "Read file: /path/to/file" (indicates potential edits)
        - Extracts unique file paths and deduplicates them
        - Sets status based on stderr presence:
          * "completed_with_errors" if stderr is not empty
          * "completed" if stderr is empty (Claude may have succeeded silently)
        - Handles empty stdout/stderr gracefully with "No output" messages

    Example:
        targets = ReviewTargets(
            artifacts_dir=Path(".epics/my-epic/artifacts"),
            updates_doc_name="epic-file-review-updates.md",
            epic_name="my-epic",
            reviewer_session_id="abc-123",
            ...
        )
        _create_fallback_updates_doc(  # noqa: E501
            targets=targets,
            stdout="Edited file: /path/to/epic.yaml\\nRead: /path/to/ticket.md",
            stderr="Warning: Some validation failed",
            builder_session_id="xyz-789"
        )
    """
    # Determine status based on stderr presence
    status = "completed_with_errors" if stderr.strip() else "completed"

    # Detect file modifications from stdout
    modified_files = _detect_modified_files(stdout)

    # Build frontmatter
    today = datetime.now().strftime("%Y-%m-%d")
    frontmatter = f"""---
date: {today}
epic: {targets.epic_name}
builder_session_id: {builder_session_id}
reviewer_session_id: {targets.reviewer_session_id}
status: {status}
---"""

    # Build status section
    status_section = """## Status

Claude did not update the template documentation file as expected.
This fallback document was automatically created to preserve the
session output and provide debugging information."""

    # Build what happened section
    what_happened = _analyze_output(stdout, stderr)
    what_happened_section = f"""## What Happened

{what_happened}"""

    # Build stdout section
    stdout_content = stdout if stdout.strip() else "No output"
    stdout_section = f"""## Standard Output

```
{stdout_content}
```"""

    # Build stderr section (only if stderr is not empty)
    stderr_section = ""
    if stderr.strip():
        stderr_section = f"""

## Standard Error

```
{stderr}
```"""

    # Build files potentially modified section
    files_section = """

## Files Potentially Modified"""
    if modified_files:
        files_section += (
            "\n\nThe following files may have been edited "
            "based on stdout analysis:\n"
        )
        for file_path in sorted(modified_files):
            files_section += f"- `{file_path}`\n"
    else:
        files_section += "\n\nNo file modifications detected in stdout."

    # Build next steps section
    next_steps_section = """

## Next Steps

1. Review the stdout and stderr logs above to understand what happened
2. Check if any files were modified by comparing timestamps
3. Manually verify the changes if files were edited
4. Review the original review artifact for recommended changes
5. Apply any missing changes manually if needed
6. Validate Priority 1 and Priority 2 fixes have been addressed"""

    # Combine all sections
    fallback_content = f"""{frontmatter}

# Epic File Review Updates

{status_section}

{what_happened_section}

{stdout_section}{stderr_section}{files_section}{next_steps_section}
"""

    # Create artifacts directory if it doesn't exist
    targets.artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Write to file with UTF-8 encoding
    output_path = targets.artifacts_dir / targets.updates_doc_name
    output_path.write_text(fallback_content, encoding="utf-8")


def _detect_modified_files(stdout: str) -> Set[str]:
    """Detect file paths that were potentially modified from stdout.

    Looks for patterns like:
    - "Edited file: /path/to/file"
    - "Wrote file: /path/to/file"
    - "Read file: /path/to/file" (may indicate edits)

    Args:
        stdout: Standard output from Claude session

    Returns:
        Set of unique file paths that were potentially modified
    """
    modified_files: Set[str] = set()

    # Pattern 1: "Edited file: /path/to/file"
    edited_pattern = r"Edited file:\s+(.+?)(?:\n|$)"
    for match in re.finditer(edited_pattern, stdout):
        file_path = match.group(1).strip()
        modified_files.add(file_path)

    # Pattern 2: "Wrote file: /path/to/file"
    wrote_pattern = r"Wrote file:\s+(.+?)(?:\n|$)"
    for match in re.finditer(wrote_pattern, stdout):
        file_path = match.group(1).strip()
        modified_files.add(file_path)

    # Pattern 3: "Read file: /path/to/file" followed by "Write" or "Edit"
    # This is more conservative - only count reads that are near writes
    read_pattern = r"Read file:\s+(.+?)(?:\n|$)"
    read_matches = list(re.finditer(read_pattern, stdout))

    # Check if there are any "Write" or "Edit" operations nearby
    has_write_operations = bool(re.search(r"(Edited|Wrote) file:", stdout))

    if has_write_operations:
        # Only include read files that appear before write operations
        for match in read_matches:
            file_path = match.group(1).strip()
            # Check if this file is mentioned in any write/edit operations
            if file_path in stdout[match.end() :]:
                modified_files.add(file_path)

    return modified_files


def _analyze_output(stdout: str, stderr: str) -> str:
    """Analyze stdout and stderr to provide insights about what happened.

    Args:
        stdout: Standard output from Claude session
        stderr: Standard error from Claude session

    Returns:
        Human-readable analysis of the session output
    """
    analysis_parts = []

    # Analyze stderr first (most critical)
    if stderr.strip():
        error_count = len(stderr.strip().split("\n"))
        analysis_parts.append(
            f"The Claude session produced error output ({error_count} lines). "
            "This indicates that something went wrong during execution. "
            "See the Standard Error section below for details."
        )

    # Analyze stdout
    if stdout.strip():
        # Check for file operations
        edit_count = len(re.findall(r"Edited file:", stdout))
        write_count = len(re.findall(r"Wrote file:", stdout))
        read_count = len(re.findall(r"Read file:", stdout))

        operation_parts = []
        if read_count > 0:
            operation_parts.append(f"{read_count} file read(s)")
        if edit_count > 0:
            operation_parts.append(f"{edit_count} file edit(s)")
        if write_count > 0:
            operation_parts.append(f"{write_count} file write(s)")

        if operation_parts:
            operations = ", ".join(operation_parts)
            analysis_parts.append(
                f"Claude performed {operations}. However, the template "
                "documentation file was not properly updated."
            )
        else:
            analysis_parts.append(
                "Claude executed but no file operation patterns were "
                "detected in stdout. The session may have completed "
                "without making changes."
            )
    else:
        analysis_parts.append(
            "No standard output was captured. The Claude session may have "
            "failed to execute or produced no output."
        )

    # Combine analysis
    if analysis_parts:
        return " ".join(analysis_parts)
    else:
        return (
            "The Claude session completed but did not update the template "
            "file. No additional information is available."
        )

def _build_feedback_prompt(
    review_content: str, targets: ReviewTargets, builder_session_id: str
) -> str:
    """Build feedback application prompt dynamically based on review type.

    Constructs a formatted prompt string for Claude to apply review feedback.
    Takes review content from the review artifact, configuration from
    ReviewTargets, and session ID from the builder. Returns a multi-section
    prompt with dynamic content based on review_type.

    The prompt instructs Claude to:
    1. Read the review feedback carefully
    2. Edit the appropriate files (based on review_type)
    3. Apply fixes in priority order (critical first, then high, medium, low)
    4. Follow important rules specific to the review type
    5. Document all changes in the updates template file

    Behavior varies based on targets.review_type:
    - "epic-file": Focuses only on the epic YAML file. Rules emphasize
      coordination requirements between tickets. Claude is told to edit
      only the primary_file (epic YAML).
    - "epic": Covers both epic YAML and all ticket markdown files. Rules
      include both epic coordination and ticket quality standards. Claude
      is told to edit primary_file AND all files in additional_files list.

    Args:
        review_content: The review feedback content from the review artifact
            (verbatim text that will be embedded in the prompt).
        targets: ReviewTargets configuration containing file paths, directories,
            and metadata for the review feedback application.
        builder_session_id: Session ID of the original epic/ticket builder
            (used in documentation frontmatter for traceability).

    Returns:
        A formatted prompt string ready to be passed to ClaudeRunner for
        execution. The prompt includes all 8 required sections with proper
        markdown formatting.

    Note:
        The builder_session_id and targets.reviewer_session_id are included
        in the prompt so Claude knows what to put in the documentation
        frontmatter for traceability.
    """
    # Build the documentation file path
    updates_doc_path = targets.artifacts_dir / targets.updates_doc_name

    # Section 1: Documentation requirement
    doc_requirement = f"""## CRITICAL REQUIREMENT: Document Your Work

You MUST create a documentation file at the end of this session.

**File path**: {updates_doc_path}

The file already exists as a template. You must REPLACE it using the
Write tool with this structure:

```markdown
---
date: {datetime.now().strftime('%Y-%m-%d')}
epic: {targets.epic_name}
builder_session_id: {builder_session_id}
reviewer_session_id: {targets.reviewer_session_id}
status: completed
---

# {("Epic File Review Updates" if targets.review_type == "epic-file"
   else "Epic Review Updates")}

## Changes Applied

### Priority 1 Fixes
[List EACH Priority 1 issue fixed with SPECIFIC changes made]

### Priority 2 Fixes
[List EACH Priority 2 issue fixed with SPECIFIC changes made]

## Changes Not Applied
[List any recommended changes NOT applied and WHY]

## Summary
[1-2 sentences describing overall improvements]
```

**IMPORTANT**: Change `status: completed` in the frontmatter. This is
how we know you finished."""

    # Section 2: Task description
    if targets.review_type == "epic-file":
        task_description = f"""## Your Task: Apply Review Feedback

You are improving an epic file based on a comprehensive review.

**Epic file**: {targets.primary_file}
**Review report below**:"""
    else:  # epic review
        task_description = f"""## Your Task: Apply Review Feedback

You are improving an epic and its tickets based on a comprehensive review.

**Epic file**: {targets.primary_file}
**Ticket files**: {', '.join(str(f) for f in targets.additional_files)}
**Review report below**:"""

    # Section 3: Review content (verbatim)
    review_section = f"\n{review_content}\n"

    # Section 4: Workflow steps
    if targets.review_type == "epic-file":
        workflow = f"""### Workflow

1. **Read** the epic file at {targets.primary_file}
2. **Identify** Priority 1 and Priority 2 issues from the review
3. **Apply fixes** using Edit tool (surgical changes only)
4. **Document** your changes by writing the file above"""
    else:  # epic review
        workflow = f"""### Workflow

1. **Read** the epic file at {targets.primary_file}
2. **Read** all ticket files in {', '.join(
   str(d) for d in targets.editable_directories)}
3. **Identify** Priority 1 and Priority 2 issues from the review
4. **Apply fixes** using Edit tool (surgical changes only)
5. **Document** your changes by writing the file above"""

    # Section 5: What to fix (prioritized)
    what_to_fix = """### What to Fix

**Priority 1 (Must Fix)**:
- Add missing function examples to ticket descriptions (Paragraph 2)
- Define missing terms (like "epic baseline") in coordination_requirements
- Add missing specifications (error handling, acceptance criteria formats)
- Fix dependency errors

**Priority 2 (Should Fix if time permits)**:
- Add integration contracts to tickets
- Clarify implementation details
- Add test coverage requirements"""

    # Section 6: Important rules (varies by review_type)
    if targets.review_type == "epic-file":
        important_rules = """### Important Rules

- ✅ **USE** Edit tool for targeted changes (NOT Write for complete rewrites)
- ✅ **PRESERVE** existing epic structure and field names
  (epic, description, ticket_count, etc.)
- ✅ **KEEP** existing ticket IDs unchanged
- ✅ **MAINTAIN** coordination requirements between tickets
- ✅ **VERIFY** changes after each edit
- ❌ **DO NOT** rewrite the entire epic
- ❌ **DO NOT** change the epic schema"""
    else:  # epic review
        important_rules = """### Important Rules

**For Epic YAML:**
- ✅ **USE** Edit tool for targeted changes (NOT Write for complete rewrites)
- ✅ **PRESERVE** existing epic structure and field names
  (epic, description, ticket_count, etc.)
- ✅ **KEEP** existing ticket IDs unchanged
- ✅ **MAINTAIN** coordination requirements between tickets
- ✅ **VERIFY** changes after each edit
- ❌ **DO NOT** rewrite the entire epic
- ❌ **DO NOT** change the epic schema

**For Ticket Markdown Files:**
- ✅ **USE** Edit tool for targeted changes
- ✅ **PRESERVE** ticket frontmatter and structure
- ✅ **ADD** missing acceptance criteria, test cases, and implementation details
- ✅ **CLARIFY** dependencies and integration points
- ✅ **VERIFY** consistency with epic coordination requirements
- ❌ **DO NOT** change ticket IDs or dependencies without coordination
- ❌ **DO NOT** rewrite entire tickets"""

    # Section 7: Example edits
    example_edits = """### Example Surgical Edit

Good approach:
```
Use Edit tool to add function examples to ticket description Paragraph 2:
- Find: "Implement git operations wrapper"
- Replace with: "Implement git operations wrapper.

  Key functions:
  - create_branch(name: str, base: str) -> None: creates branch from commit
  - push_branch(name: str) -> None: pushes branch to remote"
```"""

    # Section 8: Final documentation step
    final_step = f"""### Final Step

After all edits, use Write tool to replace {updates_doc_path}
with your documentation."""

    # Combine all sections with proper spacing
    prompt = f"""{doc_requirement}

---

{task_description}

{review_section}

{workflow}

{what_to_fix}

{important_rules}

{example_edits}

{final_step}"""

    return prompt


def apply_review_feedback(
    review_artifact_path: Path,
    builder_session_id: str,
    context: "ProjectContext",
    targets: ReviewTargets,
    console: "Console",
) -> None:
    """Orchestrate the complete review feedback application workflow.

    This is the main entry point for applying review feedback from a review
    artifact to target files (epic YAML and/or ticket markdown files). It
    coordinates all steps of the workflow: reading the review, building the
    prompt, creating the template doc, resuming the Claude session, validating
    completion, and creating fallback documentation if needed.

    Workflow Steps:
        1. Read review artifact from review_artifact_path
        2. Build feedback application prompt using _build_feedback_prompt()
        3. Create template documentation using _create_template_doc()
        4. Resume builder session with feedback prompt using subprocess
        5. Validate documentation was completed (check frontmatter status)
        6. Create fallback documentation if needed using
           _create_fallback_updates_doc()

    Error Handling:  # noqa: E501
        - FileNotFoundError: review_artifact_path missing → log, re-raise
        - yaml.YAMLError: frontmatter parsing fails → log, re-raise
        - OSError: file operations fail → log, re-raise
        - subprocess errors: Claude fails → log, create fallback, continue
        - Partial failures: some files updated → log warnings, continue

    Console Output:
        - Displays "Applying review feedback..." at start
        - Shows spinner/progress indicator during Claude execution
        - Displays success message with file change count when complete
        - Displays path to documentation artifact when complete
        - Shows error messages clearly when failures occur

    Args:
        review_artifact_path: Path to review artifact file containing
            the review feedback to apply.
        builder_session_id: Session ID of the original builder session
            (create-epic or create-tickets) to resume for applying feedback.
        context: ProjectContext for Claude execution (cwd, project_root).
        targets: ReviewTargets specifying which files to edit, where to
            write logs, and other metadata.
        console: Rich Console instance for user-facing output.

    Returns:
        None. This function has side effects only: edits files, creates logs,
        creates documentation.

    Raises:
        FileNotFoundError: If review artifact file doesn't exist.
        yaml.YAMLError: If review artifact YAML frontmatter is malformed.
        OSError: If file operations fail (directory creation, file writing).

    Side Effects:
        - Edits targets.primary_file (epic YAML)
        - Edits files in targets.additional_files (ticket markdown)
        - Creates/updates artifacts_dir/updates_doc_name (documentation)
        - Creates artifacts_dir/log_file_name (stdout log)
        - Creates artifacts_dir/error_file_name (stderr log)

    Integration:
        - Uses _build_feedback_prompt() to generate Claude prompt
        - Uses _create_template_doc() to create initial template
        - Uses _create_fallback_updates_doc() for failure recovery
        - Uses subprocess.run() to execute Claude CLI
        - Uses yaml.safe_load() to parse frontmatter

    Example:
        targets = ReviewTargets(
            primary_file=Path(".epics/my-epic/my-epic.epic.yaml"),
            additional_files=[],
            editable_directories=[Path(".epics/my-epic")],
            artifacts_dir=Path(".epics/my-epic/artifacts"),
            updates_doc_name="epic-file-review-updates.md",
            log_file_name="epic-file-review.log",
            error_file_name="epic-file-review.error.log",
            epic_name="my-epic",
            reviewer_session_id="abc-123",
            review_type="epic-file"
        )
        apply_review_feedback(
            review_artifact_path=Path(".epics/my-epic/artifacts/epic-file-review.md"),
            builder_session_id="xyz-789",
            context=context,
            targets=targets,
            console=console
        )
    """
    import logging
    import subprocess

    import yaml

    logger = logging.getLogger(__name__)

    # Display progress message
    console.print("\n[blue]Applying review feedback...[/blue]")

    try:
        # Step 1: Read review artifact
        try:
            review_content = review_artifact_path.read_text(encoding="utf-8")
            logger.info(f"Read review artifact: {review_artifact_path}")
        except FileNotFoundError:
            error_msg = f"Review artifact not found: {review_artifact_path}"
            logger.error(error_msg)
            console.print(f"[red]Error: {error_msg}[/red]")
            raise

        # Step 2: Build feedback application prompt
        try:
            feedback_prompt = _build_feedback_prompt(
                review_content=review_content,
                targets=targets,
                builder_session_id=builder_session_id,
            )
            logger.info("Built feedback application prompt")
        except Exception as e:
            error_msg = f"Failed to build feedback prompt: {e}"
            logger.error(error_msg)
            console.print(f"[red]Error: {error_msg}[/red]")
            raise

        # Step 3: Create template documentation
        try:
            _create_template_doc(
                targets=targets, builder_session_id=builder_session_id
            )
            template_doc = targets.artifacts_dir / targets.updates_doc_name
            logger.info(f"Created template documentation: {template_doc}")
        except OSError as e:
            error_msg = f"Failed to create template documentation: {e}"
            logger.error(error_msg)
            console.print(f"[red]Error: {error_msg}[/red]")
            raise

        # Step 4: Resume builder session with feedback prompt
        log_file_path = targets.artifacts_dir / targets.log_file_name
        error_file_path = targets.artifacts_dir / targets.error_file_name

        # Ensure artifacts directory exists
        targets.artifacts_dir.mkdir(parents=True, exist_ok=True)

        claude_stdout = ""
        claude_stderr = ""

        try:
            with console.status(
                "[bold cyan]Claude is applying review feedback...[/bold cyan]",
                spinner="bouncingBar",
            ):
                # Run Claude CLI subprocess and capture output
                result = subprocess.run(
                    [
                        "claude",
                        "--dangerously-skip-permissions",
                        "--resume",
                        builder_session_id,
                    ],
                    input=feedback_prompt,
                    text=True,
                    cwd=str(context.cwd),
                    capture_output=True,
                    check=False,
                )

                claude_stdout = result.stdout
                claude_stderr = result.stderr

            # Write stdout and stderr to log files
            if claude_stdout:
                log_file_path.write_text(claude_stdout, encoding="utf-8")
                logger.info(f"Wrote stdout to: {log_file_path}")

            if claude_stderr:
                error_file_path.write_text(claude_stderr, encoding="utf-8")
                logger.warning(f"Wrote stderr to: {error_file_path}")

            if result.returncode != 0:
                logger.warning(
                    f"Claude session exited with code {result.returncode}"
                )

        except Exception as e:
            error_msg = f"Claude session failed: {e}"
            logger.error(error_msg)
            console.print(f"[yellow]Warning: {error_msg}[/yellow]")

            # Don't create fallback doc - this would cause resume to skip this step
            # Just write error logs for debugging
            if claude_stderr:
                error_file_path.write_text(claude_stderr, encoding="utf-8")
                logger.warning(f"Wrote stderr to: {error_file_path}")
                console.print(f"[yellow]Error log: {error_file_path}[/yellow]")

            return

        # Step 5: Validate documentation was completed
        template_path = targets.artifacts_dir / targets.updates_doc_name
        status = "in_progress"

        try:
            if template_path.exists():
                content = template_path.read_text(encoding="utf-8")

                # Parse YAML frontmatter
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        try:
                            frontmatter = yaml.safe_load(parts[1])
                            status = frontmatter.get("status", "in_progress")
                            logger.info(
                                f"Template documentation status: {status}"
                            )
                        except yaml.YAMLError as e:
                            error_msg = (
                                f"Failed to parse template frontmatter: {e}"
                            )
                            logger.error(error_msg)
                            # Continue with default status
        except Exception as e:
            logger.warning(f"Failed to validate template documentation: {e}")

        # Step 6: Create fallback documentation if needed
        if status == "in_progress":
            logger.warning(
                "Template documentation not updated by Claude "
                "(status still in_progress)"
            )
            console.print(
                "[yellow]Claude did not complete documentation, "
                "creating fallback...[/yellow]"
            )

            _create_fallback_updates_doc(
                targets=targets,
                stdout=claude_stdout,
                stderr=claude_stderr,
                builder_session_id=builder_session_id,
            )

            fallback_doc = targets.artifacts_dir / targets.updates_doc_name
            console.print(
                f"[yellow]Fallback documentation created: "
                f"{fallback_doc}[/yellow]"
            )
            if error_file_path.exists():
                console.print(
                    f"[yellow]Check error log: {error_file_path}[/yellow]"
                )
        else:
            # Success!
            console.print("[green]Review feedback applied successfully[/green]")

            # Count files modified (if detectable from stdout)
            modified_files = _detect_modified_files(claude_stdout)
            if modified_files:
                console.print(
                    f"  [dim]• {len(modified_files)} file(s) updated[/dim]"
                )

            doc_path = targets.artifacts_dir / targets.updates_doc_name
            console.print(f"  [dim]• Documentation: {doc_path}[/dim]")

            if log_file_path.exists():
                console.print(f"  [dim]• Log: {log_file_path}[/dim]")

    except FileNotFoundError:
        # Already logged and displayed
        raise
    except yaml.YAMLError as e:
        error_msg = f"Failed to parse YAML: {e}"
        logger.error(error_msg)
        console.print(f"[red]Error: {error_msg}[/red]")
        raise
    except OSError as e:
        error_msg = f"File operation failed: {e}"
        logger.error(error_msg)
        console.print(f"[red]Error: {error_msg}[/red]")
        raise
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        logger.error(error_msg)
        console.print(f"[red]Error: {error_msg}[/red]")
        raise
