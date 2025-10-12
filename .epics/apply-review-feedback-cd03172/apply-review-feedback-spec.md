# Apply Review Feedback - Specification

## Overview

Create a reusable abstraction for applying review feedback that works across
different review types (epic-file-review, epic-review, and future review
workflows). This refactoring extracts the common pattern from
`create_epic.py:apply_review_feedback()` into a shared utility that both
`create_epic.py` and `create_tickets.py` can use via dependency injection.

## Problem Statement

Currently, review feedback application logic is duplicated and tightly coupled:

1. **`create_epic.py:524-760`** - Applies epic-file-review feedback (237 LOC)
   - Resumes builder session
   - Edits epic YAML file only
   - Creates `epic-file-review-updates.md`
   - Has fallback documentation logic

2. **`create_tickets.py`** - Needs similar logic for epic-review feedback
   - Would edit both epic YAML and ticket markdown files
   - Would create `epic-review-updates.md`
   - Should reuse the same pattern

**Problems:**

- Code duplication (will duplicate 200+ LOC)
- Inconsistent behavior between review types
- Hard to maintain (fixes must be applied twice)
- Tightly coupled to specific file paths and names
- No abstraction for different review targets

## Goals

### Primary Goals

1. **Extract shared logic** into reusable function
2. **Support multiple review types** (epic-file, epic, future)
3. **Use dependency injection** for file targets and configuration
4. **Maintain existing behavior** for `create_epic.py`
5. **Enable `create_tickets.py`** to apply epic-review feedback
6. **Preserve session resumption** pattern
7. **Keep documentation requirements** and fallback logic

### Non-Goals

- ❌ Change review artifact format
- ❌ Modify prompt construction patterns
- ❌ Alter session management strategy
- ❌ Add new review types (just support existing ones)

## Design

### Architecture

```
cli/utils/review_feedback.py (NEW)
├── ReviewTargets (dataclass)
│   ├── primary_file: Path
│   ├── additional_files: List[Path]
│   ├── editable_directories: List[Path]
│   ├── artifacts_dir: Path
│   ├── updates_doc_name: str
│   ├── log_file_name: str
│   └── epic_name: str
│
└── apply_review_feedback(...)
    ├── _build_feedback_prompt(...)
    ├── _create_template_doc(...)
    └── _create_fallback_updates_doc(...)
```

### ReviewTargets Data Structure

```python
@dataclass
class ReviewTargets:
    """
    Configuration for review feedback application via dependency injection.

    Specifies what files to edit, where to write logs, and metadata.
    """

    # Files to edit
    primary_file: Path              # Main target (epic YAML)
    additional_files: List[Path]     # Other files (ticket markdown files)
    editable_directories: List[Path] # Directories containing editable files

    # Output configuration
    artifacts_dir: Path              # Where to write outputs
    updates_doc_name: str            # Name of updates documentation file
    log_file_name: str               # Name of log file
    error_file_name: str             # Name of error file

    # Metadata
    epic_name: str                   # Epic name for documentation
    reviewer_session_id: str         # Session ID of reviewer

    # Review type
    review_type: str                 # "epic-file" or "epic"
```

### Core Function Signature

```python
def apply_review_feedback(
    review_artifact_path: str,
    builder_session_id: str,
    context: ProjectContext,
    targets: ReviewTargets,
    console: Console
) -> None:
    """
    Resume builder Claude session to apply review feedback.

    This function:
    1. Reads review artifact
    2. Builds feedback application prompt
    3. Creates template documentation
    4. Resumes builder session with feedback prompt
    5. Validates documentation was completed
    6. Creates fallback documentation if needed

    Args:
        review_artifact_path: Path to review markdown file
        builder_session_id: Session ID to resume
        context: Project context for execution
        targets: ReviewTargets specifying what to edit and where
        console: Rich console for output

    Raises:
        FileNotFoundError: If review artifact not found
        RuntimeError: If Claude execution fails critically
    """
```

### Prompt Construction Pattern

The prompt should be built dynamically based on `ReviewTargets`:

**For epic-file-review** (primary_file only):

```python
targets = ReviewTargets(
    primary_file=Path("epic.yaml"),
    additional_files=[],
    editable_directories=[],
    ...
)
# Prompt focuses on epic YAML coordination requirements
```

**For epic-review** (epic + tickets):

```python
targets = ReviewTargets(
    primary_file=Path("epic.yaml"),
    additional_files=list(tickets_dir.glob("*.md")),
    editable_directories=[tickets_dir],
    ...
)
# Prompt covers both epic YAML and ticket files
```

### Prompt Template Structure

```python
def _build_feedback_prompt(
    review_content: str,
    targets: ReviewTargets,
    builder_session_id: str
) -> str:
    """
    Build feedback application prompt based on targets.

    Template sections:
    1. Documentation requirement (with file path from targets)
    2. Task description
    3. Review content
    4. Workflow steps
    5. What to fix (prioritized)
    6. Important rules (based on targets.review_type)
    7. Example edits
    8. Final documentation step
    """
```

**Dynamic sections based on review_type:**

| Review Type | Target Files        | Prompt Focus                                                          |
| ----------- | ------------------- | --------------------------------------------------------------------- |
| `epic-file` | Epic YAML only      | Function profiles, coordination requirements, directory structure     |
| `epic`      | Epic YAML + tickets | Coordination + ticket descriptions, acceptance criteria, dependencies |

## Implementation Plan

### Phase 1: Extract to Utility Module

**New file**: `cli/utils/review_feedback.py`

**Extract from `create_epic.py`:**

1. `_create_fallback_updates_doc()` → Keep as-is (lines 473-522)
2. `apply_review_feedback()` → Refactor with ReviewTargets (lines 524-760)
3. Prompt building logic → Extract to `_build_feedback_prompt()`
4. Template creation → Extract to `_create_template_doc()`

**Add new:**

1. `ReviewTargets` dataclass
2. Documentation for all functions
3. Type hints

### Phase 2: Refactor `create_epic.py`

**Changes:**

1. Import `apply_review_feedback` and `ReviewTargets`
2. Remove local `apply_review_feedback()` function
3. Create `ReviewTargets` instance at call site
4. Call shared function

**Before:**

```python
apply_review_feedback(
    review_artifact, str(epic_path), session_id, context
)
```

**After:**

```python
from cli.utils.review_feedback import apply_review_feedback, ReviewTargets

targets = ReviewTargets(
    primary_file=Path(epic_path),
    additional_files=[],
    editable_directories=[],
    artifacts_dir=Path(epic_path).parent / "artifacts",
    updates_doc_name="epic-file-review-updates.md",
    log_file_name="epic-feedback-application.log",
    error_file_name="epic-feedback-application.errors",
    epic_name=Path(epic_path).stem.replace('.epic', ''),
    reviewer_session_id=reviewer_session_id,
    review_type="epic-file"
)

apply_review_feedback(
    review_artifact_path=review_artifact,
    builder_session_id=session_id,
    context=context,
    targets=targets,
    console=console
)
```

### Phase 3: Integrate into `create_tickets.py`

**Add after epic-review completion:**

```python
# After invoke_epic_review() succeeds
if review_artifact:
    console.print(f"[green]✓ Review complete: {review_artifact}[/green]")

    # Apply review feedback
    tickets_dir = epic_file_path.parent / "tickets"

    targets = ReviewTargets(
        primary_file=epic_file_path,
        additional_files=list(tickets_dir.glob("*.md")),
        editable_directories=[tickets_dir],
        artifacts_dir=epic_file_path.parent / "artifacts",
        updates_doc_name="epic-review-updates.md",
        log_file_name="epic-review-application.log",
        error_file_name="epic-review-application.errors",
        epic_name=epic_file_path.stem.replace('.epic', ''),
        reviewer_session_id=review_session_id,
        review_type="epic"
    )

    apply_review_feedback(
        review_artifact_path=review_artifact,
        builder_session_id=session_id,
        context=context,
        targets=targets,
        console=console
    )
```

### Phase 4: Testing

**Unit tests** (`tests/unit/utils/test_review_feedback.py`):

1. `test_review_targets_creation()` - Dataclass instantiation
2. `test_build_feedback_prompt_epic_file()` - Epic-file review prompt
3. `test_build_feedback_prompt_epic()` - Epic review prompt
4. `test_create_template_doc()` - Template generation
5. `test_create_fallback_doc()` - Fallback documentation

**Integration tests** (manual for now):

1. Run `buildspec create-epic` with review → verify epic YAML edited
2. Run `buildspec create-tickets` with review → verify tickets + epic edited
3. Verify documentation artifacts created correctly

## File Changes

### New Files

```
cli/utils/review_feedback.py          # New utility module (~250 LOC)
tests/unit/utils/test_review_feedback.py  # Unit tests (~150 LOC)
```

### Modified Files

```
cli/commands/create_epic.py
  - Remove apply_review_feedback() function (lines 524-760, -237 LOC)
  - Remove _create_fallback_updates_doc() (lines 473-522, -50 LOC)
  - Add import and ReviewTargets creation (~15 LOC)
  - Net: -272 LOC

cli/commands/create_tickets.py
  - Add import (~2 LOC)
  - Add apply_review_feedback() call after epic-review (~25 LOC)
  - Net: +27 LOC

cli/utils/__init__.py
  - Export ReviewTargets and apply_review_feedback
```

### Net LOC Change

```
Before:
  create_epic.py:    1014 LOC
  create_tickets.py:  196 LOC
  Total:             1210 LOC

After:
  create_epic.py:     742 LOC (-272)
  create_tickets.py:  223 LOC (+27)
  review_feedback.py: 250 LOC (new)
  Total:             1215 LOC (+5)
```

Slight increase due to abstraction overhead, but much better maintainability.

## Prompts and Documentation

### Feedback Application Prompt Template

````python
FEEDBACK_PROMPT_TEMPLATE = """## CRITICAL REQUIREMENT: Document Your Work

You MUST create a documentation file at the end of this session.

**File path**: {artifacts_dir}/{updates_doc_name}

The file already exists as a template. You must REPLACE it using the Write tool with this structure:

```markdown
---
date: {date}
epic: {epic_name}
builder_session_id: {builder_session_id}
reviewer_session_id: {reviewer_session_id}
status: completed
---

# {review_type_title} Updates

## Changes Applied

### Critical Issues Fixed
[List EACH critical issue fixed with SPECIFIC changes made]

### Major Improvements Implemented
[List EACH major improvement with SPECIFIC changes made]

### Minor Issues Fixed
[List minor issues addressed]

## Changes Not Applied
[List any recommended changes NOT applied and WHY]

## Files Modified
{files_modified_section}

## Summary
[1-2 sentences describing overall improvements]
````

**IMPORTANT**: Change `status: completed` in the frontmatter. This is how we
know you finished.

---

## Your Task: Apply {review_type_title} Feedback

{task_description}

**Review report below**:

{review_content}

### Workflow

1. **Read** {read_targets}
2. **Identify** Critical Issues, Major Improvements, and Minor Issues from
   review
3. **Apply fixes** using Edit tool (surgical changes only)
4. **Document** your changes by writing the file above

### What to Fix

**Critical Issues (Must Fix)**: {critical_issues_guidance}

**Major Improvements (Should Fix if time permits)**:
{major_improvements_guidance}

### Important Rules

- ✅ **USE** Edit tool for targeted changes (NOT Write for complete rewrites)
- ✅ **PRESERVE** existing structure and formatting
- ✅ **KEEP** existing IDs and file names unchanged
- ✅ **VERIFY** changes after each edit {review_specific_rules}
- ❌ **DO NOT** rewrite entire files
- ❌ **DO NOT** change schemas
- ❌ **DO NOT** modify the spec file

### Example Surgical Edit

{example_edit}

### Final Step

After all edits, use Write tool to replace {artifacts_dir}/{updates_doc_name}
with your documentation. """

````

**Dynamic sections by review_type:**

**epic-file:**
- `task_description`: "You are improving an epic YAML file based on file review."
- `read_targets`: "the epic YAML file"
- `review_specific_rules`: "✅ **UPDATE** coordination requirements, function profiles, directory structure"
- `example_edit`: Epic YAML function signature example

**epic:**
- `task_description`: "You are improving an epic and its ticket files based on comprehensive review."
- `read_targets`: "the epic YAML and all ticket files"
- `review_specific_rules`: "✅ **UPDATE** both epic YAML coordination requirements AND ticket files"
- `example_edit`: Ticket description improvement example

### Template Documentation Content

```python
TEMPLATE_DOC_CONTENT = """---
date: {date}
epic: {epic_name}
builder_session_id: {builder_session_id}
reviewer_session_id: {reviewer_session_id}
status: in_progress
---

# {review_type_title} Updates

**Status**: 🔄 IN PROGRESS

## Changes Being Applied

Claude is currently applying {review_type} feedback. This document will be updated with:
- Critical issues fixed
- Major improvements implemented
- Minor issues addressed
- List of modified files

If you see this message, Claude may not have finished documenting changes.
Check the file modification time and compare with the review artifact.
"""
````

## Edge Cases and Error Handling

### Edge Cases

1. **Review artifact missing** → Error early with clear message
2. **Builder session invalid** → Claude will fail, caught by returncode check
3. **No files to edit** → Still run (may update documentation/coordination)
4. **Claude doesn't update template** → Fallback documentation created
5. **Partial completion** → Fallback doc lists what happened

### Error Handling Strategy

```python
try:
    apply_review_feedback(...)
except FileNotFoundError as e:
    console.print(f"[red]ERROR:[/red] Review artifact not found: {e}")
    # Don't fail command - review is optional enhancement
except Exception as e:
    console.print(f"[yellow]Warning:[/yellow] Could not apply review feedback: {e}")
    # Log but continue - tickets/epic are already created
```

**Philosophy**: Review feedback application is an **enhancement**, not a
requirement. If it fails, the epic/tickets are still usable.

## Success Criteria

### Functional Requirements

- ✅ `create_epic.py` continues to work exactly as before
- ✅ `create_tickets.py` applies epic-review feedback to epic + tickets
- ✅ Both commands create appropriate documentation artifacts
- ✅ Both commands handle failures gracefully with fallback docs
- ✅ Session resumption works correctly
- ✅ File modifications are surgical (Edit tool, not Write)

### Code Quality Requirements

- ✅ No code duplication between commands
- ✅ Clear separation of concerns (data vs. logic)
- ✅ Dependency injection via ReviewTargets
- ✅ Type hints on all functions
- ✅ Docstrings on public functions
- ✅ Unit test coverage ≥ 80%

### Maintainability Requirements

- ✅ Future review types can be added by creating new ReviewTargets
- ✅ Prompt templates are easy to modify
- ✅ Error messages are clear and actionable
- ✅ Logging provides debugging context

## Future Extensions

This abstraction enables:

1. **New review types** - Just create ReviewTargets config
2. **Manual review application** - CLI command
   `buildspec apply-review <review-artifact>`
3. **Batch review application** - Apply multiple reviews at once
4. **Review diff preview** - Show what would change before applying
5. **Rollback support** - Undo applied changes if needed

## Dependencies

### Required Imports

```python
# Standard library
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Project imports
from cli.core.claude import ClaudeRunner
from cli.core.context import ProjectContext
from rich.console import Console
```

### No New Dependencies

All required packages already in `pyproject.toml`:

- `rich` - Console output
- `pyyaml` - Already used for epic parsing

## Open Questions

1. **Should we validate targets?** - e.g., ensure primary_file exists before
   running?
2. **Error recovery** - If Claude fails mid-edit, how to recover?
3. **Concurrent edits** - What if user modifies files during feedback
   application?
4. **Dry-run mode** - Should we support preview mode?

## References

- **Existing implementation**: `cli/commands/create_epic.py:524-760`
- **Pattern source**: Epic file review workflow
- **Integration point 1**: `create_epic.py:965-969`
- **Integration point 2**: `create_tickets.py:177-189`
