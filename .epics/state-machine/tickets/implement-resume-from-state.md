# State machine resumption from epic-state.json

**Ticket ID:** implement-resume-from-state

**Critical:** false

**Dependencies:** core-state-machine

**Coordination Role:** Provides resumability for state machine after interruption

## Description

As a developer, I want state machine resumption from epic-state.json so that epic execution can recover from crashes, interruptions, or manual stops without losing progress.

This ticket enhances __init__ method in state_machine.py (ticket: core-state-machine) to support resume=True flag that loads state from existing epic-state.json file. The state machine validates loaded state for consistency and continue execution from current state (skipping completed tickets). Key logic to implement:
- __init__(epic_file: Path, resume: bool): If resume and state_file.exists() call _load_state(), else call _initialize_new_epic(), validate epic_file matches loaded state
- _load_state(): Read epic-state.json, parse JSON, reconstruct Ticket objects with all fields from state, reconstruct EpicContext with loaded state, validate consistency (_validate_loaded_state), log resumed state
- _validate_loaded_state(): Check tickets in valid states, verify git branches exist for IN_PROGRESS/COMPLETED tickets via context.git.branch_exists_remote(), verify epic branch exists, check state file schema version

## Acceptance Criteria

- State loaded from epic-state.json with all ticket fields reconstructed (including git_info, timestamps, failure_reason)
- State validation detects inconsistencies (missing branches, invalid states, schema mismatch)
- execute() continues from current state (COMPLETED tickets skipped, IN_PROGRESS tickets fail and retry, READY tickets execute)
- Resume flag required to prevent accidental resume
- Missing state file with resume=True raises FileNotFoundError with clear message

## Testing

Unit tests for _load_state with valid and invalid JSON. Unit tests for _validate_loaded_state with various inconsistencies. Integration test that creates epic, executes 1 ticket, saves state, stops, resumes, verifies completion. Coverage: 85% minimum.

## Non-Goals

No state file migration/versioning, no partial state recovery, no state history/audit trail, no corrupt state repair.
