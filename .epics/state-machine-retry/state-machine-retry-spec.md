# Epic Retry & Resumption System - Specification

## Overview

Enable robust retry and resumption for `buildspec execute-epic` so that interrupted or failed epic executions can be resumed seamlessly by re-running the same command. The system must handle partial ticket builds, uncommitted work, and git state cleanup automatically.

## Problem Statement

When `buildspec execute-epic` is interrupted (crash, Ctrl-C, timeout, system failure), the epic is left in a partially-completed state:

1. **Partial ticket build**: A ticket was IN_PROGRESS when interruption occurred, potentially with:
   - Uncommitted changes in working directory
   - Partial implementation (some files modified, others not)
   - Tests not run or incomplete
   - No final commit SHA recorded

2. **State file inconsistency**: `epic-state.json` shows ticket as IN_PROGRESS but builder subprocess is dead

3. **Git pollution**: Working directory may have uncommitted changes from the interrupted ticket

4. **User friction**: User must manually diagnose state, clean up git, and figure out how to restart

## Goals

1. **Zero-friction resume**: User runs `buildspec execute-epic path/to/epic/` again → execution continues from where it left off
2. **Automatic cleanup**: System detects partial builds and handles them automatically (rollback uncommitted work)
3. **Deterministic recovery**: Same inputs always produce same recovery behavior
4. **Safe by default**: Never silently lose work or corrupt state
5. **Clear feedback**: User understands what happened and what the system is doing

## Non-Goals

- Manual state manipulation commands (`buildspec epic status`, `buildspec epic reset`)
- Retry logic for transient LLM failures (separate concern)
- Concurrent epic execution
- State migration or versioning (covered by schema_version field)
- Git worktree support

## Architecture

### Resume Detection

When `EpicStateMachine.__init__()` is called:

```python
def __init__(self, epic_file: Path, resume: bool = False):
    # If state file exists, always resume (ignore resume flag for now)
    if self.state_file.exists():
        self._resume_from_state()
    else:
        self._initialize_new_epic()
```

**Decision**: Make resumption automatic when state file exists. The `resume` flag becomes a safety mechanism to prevent accidental overwrites, but default behavior is "smart resume."

### State Recovery Process

When resuming from `epic-state.json`:

```
1. Load state file
2. Validate state consistency
3. Detect partial builds (tickets in IN_PROGRESS or AWAITING_VALIDATION)
4. For each partial build:
   a. Check git working directory status
   b. If uncommitted changes exist → rollback ticket to READY state
   c. If clean → validate git state consistency
5. Resume execution from current state
```

### Rollback Strategy for Partial Builds

**Key insight**: If a ticket is IN_PROGRESS but builder is not running, it MUST be rolled back to READY and re-executed.

#### Rollback Logic

```python
def _handle_partial_ticket(self, ticket: Ticket) -> None:
    """Handle ticket that was interrupted mid-execution.

    Strategy:
    1. Check if working directory has uncommitted changes
    2. If yes: stash or reset, transition ticket to READY
    3. Delete any partial commits on ticket branch (if they exist)
    4. Ticket will be re-executed from scratch
    """

    # Check working directory status
    if self._has_uncommitted_changes():
        logger.warning(f"Ticket {ticket.id} has uncommitted changes - rolling back")
        self._cleanup_working_directory()

    # Check if ticket branch has any commits beyond base
    if ticket.git_info and ticket.git_info.branch_name:
        commits = self.git.get_commits_between(
            ticket.git_info.base_commit,
            ticket.git_info.branch_name
        )

        if len(commits) > 0:
            logger.warning(
                f"Ticket {ticket.id} has partial commits - will be reset"
            )
            # Reset branch to base commit (destructive but correct)
            self._reset_ticket_branch(ticket)

    # Transition ticket back to READY (it will be re-executed)
    ticket.git_info = GitInfo(
        branch_name=ticket.git_info.branch_name if ticket.git_info else None,
        base_commit=ticket.git_info.base_commit if ticket.git_info else None,
        final_commit=None  # Clear final commit
    )
    ticket.started_at = None
    ticket.test_suite_status = None
    ticket.acceptance_criteria = []
    self._transition_ticket(ticket.id, TicketState.READY)
```

### Git State Validation

Before resuming, validate that git state matches expectations:

```python
def _validate_git_state(self) -> list[str]:
    """Validate git state consistency with state file.

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Check epic branch exists
    if not self.git.branch_exists_remote(self.epic_branch):
        errors.append(f"Epic branch {self.epic_branch} not found on remote")

    # Check completed tickets have branches
    for ticket in self.tickets.values():
        if ticket.state == TicketState.COMPLETED:
            if not ticket.git_info or not ticket.git_info.branch_name:
                errors.append(
                    f"Completed ticket {ticket.id} missing git_info"
                )
            elif not self.git.branch_exists_remote(ticket.git_info.branch_name):
                errors.append(
                    f"Completed ticket {ticket.id} branch not found: "
                    f"{ticket.git_info.branch_name}"
                )

            # Verify final commit exists
            if ticket.git_info.final_commit:
                if not self.git.commit_exists(ticket.git_info.final_commit):
                    errors.append(
                        f"Ticket {ticket.id} final commit not found: "
                        f"{ticket.git_info.final_commit}"
                    )

    return errors
```

### Working Directory Cleanup

Handle uncommitted changes safely:

```python
def _cleanup_working_directory(self) -> None:
    """Clean up uncommitted changes in working directory.

    Strategy:
    - If we're on a ticket branch, reset hard to base commit
    - If we're on epic or main branch, stash changes (safer)
    - Log what was cleaned up for transparency
    """
    # Get current branch
    result = self.git._run_git_command(["git", "branch", "--show-current"])
    current_branch = result.stdout.strip()

    # Get status for logging
    result = self.git._run_git_command(["git", "status", "--short"])
    dirty_files = result.stdout.strip()

    if dirty_files:
        logger.warning(
            f"Working directory has uncommitted changes:\n{dirty_files}"
        )

        # If on ticket branch, hard reset to base commit
        if current_branch.startswith("ticket/"):
            ticket_id = current_branch.replace("ticket/", "")
            if ticket_id in self.tickets:
                ticket = self.tickets[ticket_id]
                if ticket.git_info and ticket.git_info.base_commit:
                    logger.warning(
                        f"Resetting {current_branch} to base commit "
                        f"{ticket.git_info.base_commit[:8]}"
                    )
                    self.git._run_git_command([
                        "git", "reset", "--hard", ticket.git_info.base_commit
                    ])
                    return

        # Default: stash changes (safer fallback)
        logger.warning("Stashing uncommitted changes")
        self.git._run_git_command([
            "git", "stash", "push", "-u",
            "-m", f"buildspec-auto-stash-{datetime.utcnow().isoformat()}"
        ])

def _reset_ticket_branch(self, ticket: Ticket) -> None:
    """Reset ticket branch to base commit, discarding partial work.

    This is destructive but necessary for clean retry.
    """
    if not ticket.git_info or not ticket.git_info.branch_name:
        return

    # Checkout ticket branch
    self.git._run_git_command([
        "git", "checkout", ticket.git_info.branch_name
    ])

    # Hard reset to base commit
    self.git._run_git_command([
        "git", "reset", "--hard", ticket.git_info.base_commit
    ])

    # Force push to remote (destructive)
    self.git._run_git_command([
        "git", "push", "--force", "origin", ticket.git_info.branch_name
    ])

    logger.info(
        f"Reset {ticket.git_info.branch_name} to {ticket.git_info.base_commit[:8]}"
    )
```

## State Machine Integration

### Modified `__init__` Method

```python
def __init__(self, epic_file: Path, resume: bool = False):
    """Initialize the state machine.

    Args:
        epic_file: Path to the epic YAML file
        resume: If True, require state file to exist (safety check)

    Raises:
        FileNotFoundError: If epic file or required state file doesn't exist
        ValueError: If state file is corrupted or inconsistent
    """
    self.epic_file = epic_file
    self.epic_dir = epic_file.parent
    self.state_file = self.epic_dir / "artifacts" / "epic-state.json"

    # Determine if resuming
    state_exists = self.state_file.exists()

    if resume and not state_exists:
        raise FileNotFoundError(
            f"Resume requested but no state file found: {self.state_file}\n"
            f"Did you mean to start a new epic execution?"
        )

    if state_exists:
        logger.info(f"Resuming epic from state file: {self.state_file}")
        self._resume_from_state()
    else:
        logger.info(f"Starting new epic execution: {epic_file}")
        self._initialize_new_epic()
```

### New `_resume_from_state` Method

```python
def _resume_from_state(self) -> None:
    """Resume epic execution from existing state file.

    Process:
    1. Load and parse state file
    2. Validate state consistency
    3. Handle partial builds (IN_PROGRESS tickets)
    4. Validate git state
    5. Continue execution
    """
    # Load state file
    try:
        with open(self.state_file, "r") as f:
            state_data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Corrupted state file: {e}") from e

    # Validate schema version
    schema_version = state_data.get("schema_version", 0)
    if schema_version != 1:
        raise ValueError(
            f"Unsupported state file schema version: {schema_version}\n"
            f"Expected version 1. State file may be from different "
            f"buildspec version."
        )

    # Extract epic metadata
    self.epic_id = state_data["epic_id"]
    self.epic_branch = state_data["epic_branch"]
    self.baseline_commit = state_data["baseline_commit"]
    self.epic_state = EpicState(state_data["epic_state"])

    # Load epic configuration (still needed for coordination requirements)
    with open(self.epic_file, "r") as f:
        self.epic_config = yaml.safe_load(f)

    # Initialize git operations
    self.git = GitOperations()

    # Reconstruct tickets from state
    self.tickets = {}
    for ticket_id, ticket_data in state_data["tickets"].items():
        git_info_data = ticket_data.get("git_info")
        git_info = None
        if git_info_data:
            git_info = GitInfo(
                branch_name=git_info_data.get("branch_name"),
                base_commit=git_info_data.get("base_commit"),
                final_commit=git_info_data.get("final_commit"),
            )

        acceptance_criteria = [
            AcceptanceCriterion(
                criterion=ac["criterion"],
                met=ac["met"]
            )
            for ac in ticket_data.get("acceptance_criteria", [])
        ]

        ticket = Ticket(
            id=ticket_data["id"],
            path=ticket_data["path"],
            title=ticket_data["title"],
            depends_on=ticket_data.get("depends_on", []),
            critical=ticket_data.get("critical", False),
            state=TicketState(ticket_data["state"]),
            git_info=git_info,
            test_suite_status=ticket_data.get("test_suite_status"),
            acceptance_criteria=acceptance_criteria,
            failure_reason=ticket_data.get("failure_reason"),
            blocking_dependency=ticket_data.get("blocking_dependency"),
            started_at=ticket_data.get("started_at"),
            completed_at=ticket_data.get("completed_at"),
        )

        self.tickets[ticket_id] = ticket

    # Create epic context
    self.context = EpicContext(
        epic_id=self.epic_id,
        epic_branch=self.epic_branch,
        baseline_commit=self.baseline_commit,
        tickets=self.tickets,
        git=self.git,
        epic_config=self.epic_config,
    )

    # Validate git state consistency
    git_errors = self._validate_git_state()
    if git_errors:
        logger.error("Git state validation failed:")
        for error in git_errors:
            logger.error(f"  - {error}")
        raise ValueError(
            f"Git state inconsistent with state file. "
            f"Found {len(git_errors)} errors. "
            f"See logs for details."
        )

    # Handle partial builds
    partial_tickets = [
        t for t in self.tickets.values()
        if t.state in [TicketState.IN_PROGRESS, TicketState.AWAITING_VALIDATION]
    ]

    if partial_tickets:
        logger.warning(
            f"Found {len(partial_tickets)} partial builds - rolling back"
        )
        for ticket in partial_tickets:
            self._handle_partial_ticket(ticket)

    # Log resume summary
    completed_count = sum(
        1 for t in self.tickets.values() if t.state == TicketState.COMPLETED
    )
    pending_count = sum(
        1 for t in self.tickets.values()
        if t.state in [TicketState.PENDING, TicketState.READY]
    )
    failed_count = sum(
        1 for t in self.tickets.values() if t.state == TicketState.FAILED
    )

    logger.info(
        f"Resumed epic: {self.epic_id} "
        f"(completed: {completed_count}, "
        f"pending: {pending_count}, "
        f"failed: {failed_count})"
    )
```

## CLI Command Interface

The `buildspec execute-epic` command interface should be simple:

```bash
# Start new epic execution
buildspec execute-epic path/to/epic.epic.yaml

# Resume automatically (state file detected)
buildspec execute-epic path/to/epic.epic.yaml

# Force new execution (ignore existing state)
buildspec execute-epic path/to/epic.epic.yaml --force-new

# Resume with explicit flag (safety check)
buildspec execute-epic path/to/epic.epic.yaml --resume
```

### CLI Implementation Changes

```python
def command(
    epic_file: str = typer.Argument(..., help="Path to epic YAML file"),
    resume: bool = typer.Option(
        False, "--resume", help="Require state file to exist (safety check)"
    ),
    force_new: bool = typer.Option(
        False,
        "--force-new",
        help="Start new execution, archiving existing state file"
    ),
    project_dir: Optional[Path] = typer.Option(
        None, "--project-dir", "-p", help="Project directory"
    ),
):
    """Execute entire epic with dependency management.

    If a state file exists, execution automatically resumes from where it left off.
    Partial builds (IN_PROGRESS tickets) are rolled back and re-executed.
    """
    try:
        # Resolve epic file path
        epic_file_path = resolve_file_argument(
            epic_file, expected_pattern="epic", arg_name="epic file"
        )

        # Initialize context
        context = ProjectContext(cwd=project_dir)

        # Check for existing state file
        state_file = epic_file_path.parent / "artifacts" / "epic-state.json"

        if force_new and state_file.exists():
            # Archive existing state file
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            archive_path = state_file.with_suffix(f".{timestamp}.json")
            state_file.rename(archive_path)
            console.print(
                f"[yellow]Archived existing state:[/yellow] {archive_path}"
            )

        # Initialize state machine (handles resume automatically)
        state_machine = EpicStateMachine(
            epic_file=epic_file_path,
            resume=resume
        )

        # Execute
        state_machine.execute()

        console.print("\n[green]✓ Epic execution completed[/green]")

    except Exception as e:
        console.print(f"[red]ERROR:[/red] {e}")
        raise typer.Exit(code=1) from e
```

## User Experience

### Scenario 1: Interrupted Mid-Ticket

```bash
$ buildspec execute-epic .epics/my-feature/my-feature.epic.yaml
[INFO] Starting new epic execution: my-feature
[INFO] Executing ticket: ticket-1
[INFO] Ticket ticket-1: PENDING -> READY
[INFO] Ticket ticket-1: READY -> BRANCH_CREATED
[INFO] Ticket ticket-1: BRANCH_CREATED -> IN_PROGRESS
[INFO] Spawning builder for ticket: ticket-1
^C  # User hits Ctrl-C

$ buildspec execute-epic .epics/my-feature/my-feature.epic.yaml
[INFO] Resuming epic from state file: .epics/my-feature/artifacts/epic-state.json
[WARNING] Found 1 partial builds - rolling back
[WARNING] Ticket ticket-1 has uncommitted changes - rolling back
[WARNING] Stashing uncommitted changes
[INFO] Ticket ticket-1: IN_PROGRESS -> READY
[INFO] Resumed epic: my-feature (completed: 0, pending: 3, failed: 0)
[INFO] Executing ticket: ticket-1  # Starts fresh
[INFO] Ticket ticket-1: READY -> BRANCH_CREATED
[INFO] Ticket ticket-1: BRANCH_CREATED -> IN_PROGRESS
[INFO] Spawning builder for ticket: ticket-1
[INFO] Builder succeeded for ticket: ticket-1
[INFO] Ticket ticket-1: IN_PROGRESS -> AWAITING_VALIDATION
[INFO] Running gate ValidationGate for ticket ticket-1
[INFO] Gate ValidationGate passed for ticket ticket-1
[INFO] Ticket ticket-1: AWAITING_VALIDATION -> COMPLETED
[INFO] Ticket completed: ticket-1
...
```

### Scenario 2: Clean Restart After Completion

```bash
$ buildspec execute-epic .epics/my-feature/my-feature.epic.yaml
[INFO] Resuming epic from state file: .epics/my-feature/artifacts/epic-state.json
[INFO] Resumed epic: my-feature (completed: 3, pending: 0, failed: 0)
[INFO] All tickets completed - finalizing epic
[INFO] Finalizing epic (placeholder)
[INFO] Epic execution complete
✓ Epic execution completed
```

### Scenario 3: Failed Ticket Retry

```bash
$ buildspec execute-epic .epics/my-feature/my-feature.epic.yaml
[INFO] Resuming epic from state file: .epics/my-feature/artifacts/epic-state.json
[INFO] Resumed epic: my-feature (completed: 1, pending: 1, failed: 1)
[ERROR] Epic failed: 1 failed tickets, 0 blocked tickets
ERROR: Epic execution failed
```

User fixes the issue, then:

```bash
$ buildspec execute-epic .epics/my-feature/my-feature.epic.yaml --force-new
[YELLOW] Archived existing state: .epics/my-feature/artifacts/epic-state.20241012-143022.json
[INFO] Starting new epic execution: my-feature
...
```

## Safety Guarantees

1. **Idempotency**: Running resume multiple times with same state produces same result
2. **No silent data loss**: Uncommitted changes are stashed (logged), not discarded
3. **Partial build detection**: IN_PROGRESS tickets always rolled back (never assumed complete)
4. **Git consistency**: Validation ensures completed tickets have valid commits/branches
5. **Clear logging**: Every cleanup action is logged with details
6. **Atomic state writes**: State file writes remain atomic (existing pattern)

## Edge Cases

### 1. State File Corrupted

```python
# In _resume_from_state()
except json.JSONDecodeError as e:
    raise ValueError(
        f"State file corrupted: {e}\n"
        f"Path: {self.state_file}\n"
        f"Recommendation: Archive or delete state file and restart"
    )
```

### 2. Git Branch Deleted Externally

```python
# In _validate_git_state()
if ticket.state == TicketState.COMPLETED:
    if not self.git.branch_exists_remote(ticket.git_info.branch_name):
        errors.append(
            f"Completed ticket {ticket.id} branch deleted externally: "
            f"{ticket.git_info.branch_name}"
        )
```

User sees error and can:
- Restore branch from backup
- Or `--force-new` to start fresh

### 3. Multiple IN_PROGRESS Tickets (Impossible by Design)

The `LLMStartGate` ensures only one ticket can be IN_PROGRESS at a time. If state file shows multiple, it's corruption → fail fast.

### 4. Working Directory on Wrong Branch

```python
# In _cleanup_working_directory()
result = self.git._run_git_command(["git", "branch", "--show-current"])
current_branch = result.stdout.strip()

# If on unexpected branch, log warning but proceed
if not current_branch.startswith("ticket/") and current_branch != self.epic_branch:
    logger.warning(
        f"Working directory on unexpected branch: {current_branch}\n"
        f"Expected ticket branch or epic branch: {self.epic_branch}"
    )
```

### 5. Partial Commit on Ticket Branch

```python
# In _handle_partial_ticket()
commits = self.git.get_commits_between(
    ticket.git_info.base_commit,
    ticket.git_info.branch_name
)

if len(commits) > 0:
    logger.warning(
        f"Ticket {ticket.id} has {len(commits)} partial commits - "
        f"these will be discarded"
    )
    self._reset_ticket_branch(ticket)
```

This is **destructive but correct**: partial work must be discarded to ensure clean retry.

## Implementation Plan

### Phase 1: Core Resume Logic
- Implement `_resume_from_state()` method
- Implement `_load_state()` with schema validation
- Implement `_validate_git_state()` for consistency checks
- Update `__init__()` to detect and load state automatically

### Phase 2: Partial Build Handling
- Implement `_handle_partial_ticket()` for rollback logic
- Implement `_cleanup_working_directory()` for git cleanup
- Implement `_reset_ticket_branch()` for destructive reset
- Add `_has_uncommitted_changes()` helper

### Phase 3: CLI Integration
- Add `--resume` flag to `execute-epic` command
- Add `--force-new` flag for fresh starts
- Update help text and error messages
- Add resume detection logging

### Phase 4: Testing
- Integration test: interrupt mid-ticket, resume, verify completion
- Integration test: complete epic, resume (no-op), verify idempotency
- Integration test: partial commits on ticket branch, verify reset
- Unit tests: `_validate_git_state()` with various inconsistencies
- Unit tests: `_handle_partial_ticket()` with different git states

## Testing Strategy

### Integration Tests

1. **test_resume_after_interrupt**: Simulate Ctrl-C during ticket execution, verify resume works
2. **test_resume_with_uncommitted_changes**: Leave dirty working directory, verify cleanup
3. **test_resume_with_partial_commits**: Create partial commits on ticket branch, verify reset
4. **test_resume_idempotency**: Resume multiple times, verify no-op behavior
5. **test_force_new_archives_state**: Use --force-new, verify state archived
6. **test_resume_validation_errors**: Simulate missing branch, verify clear error

### Unit Tests

1. **test_load_state_valid**: Load valid state file, verify reconstruction
2. **test_load_state_corrupted**: Load corrupted JSON, verify error
3. **test_load_state_wrong_version**: Load v0 state file, verify error
4. **test_validate_git_state_missing_branch**: Missing branch, verify error
5. **test_validate_git_state_missing_commit**: Missing commit, verify error
6. **test_handle_partial_ticket_clean**: IN_PROGRESS with clean git, verify rollback
7. **test_handle_partial_ticket_dirty**: IN_PROGRESS with uncommitted changes, verify cleanup
8. **test_handle_partial_ticket_partial_commits**: IN_PROGRESS with partial commits, verify reset

## Success Criteria

1. ✅ User can Ctrl-C during epic execution and resume by re-running same command
2. ✅ Partial ticket builds are automatically detected and rolled back
3. ✅ Uncommitted changes are stashed (not lost) with clear logging
4. ✅ Git state validation catches inconsistencies with helpful errors
5. ✅ Resume is idempotent (multiple resumes with same state = no-op)
6. ✅ Integration tests verify end-to-end resume workflow
7. ✅ Clear user feedback during resume (what's being rolled back, why)

## Open Questions

1. **Stash vs. Hard Reset**: Should we stash uncommitted changes or hard reset?
   - **Recommendation**: Stash by default (safer), hard reset only on ticket branches (cleaner)

2. **Partial commits**: Should we try to preserve partial commits or always reset?
   - **Recommendation**: Always reset (simpler, more reliable, no ambiguity)

3. **State file versioning**: Should we support migration from v0 to v1?
   - **Recommendation**: No migration in initial implementation (fail fast with clear error)

4. **Concurrent execution**: What if user runs two `execute-epic` commands simultaneously?
   - **Recommendation**: Out of scope (state machine enforces single ticket execution, not single state machine instance)

5. **Manual state editing**: Should we detect if user manually edited state file?
   - **Recommendation**: No validation beyond JSON schema (trust state file, fail if inconsistent)

## Summary

This retry system makes epic execution robust and user-friendly by:

1. **Automatic resume**: Detecting existing state and continuing execution
2. **Smart cleanup**: Handling partial builds with git rollback
3. **Clear feedback**: Logging all cleanup actions and resume decisions
4. **Safe defaults**: Stashing changes, validating consistency
5. **Simple UX**: Re-run same command to resume

The key insight is that **partial builds must always be rolled back** because we can't trust incomplete work from an interrupted builder subprocess. This makes resume logic simple and deterministic: if ticket is IN_PROGRESS → rollback to READY → re-execute.
