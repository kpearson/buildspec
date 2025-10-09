# implement-state-file-persistence

## Description
Add state file loading and atomic saving to state machine

## Epic Context
This ticket implements the persistence layer that enables resumability - a key objective of the state machine. The state file allows the state machine to recover from crashes and continue execution from the exact point of failure.

**Key Objectives**:
- Resumability: State machine can resume from epic-state.json after crashes
- Auditable Execution: State machine logs all transitions and gate checks for debugging

**Key Constraints**:
- State machine can resume mid-epic execution from state file
- State file (epic-state.json) is private to state machine
- Epic execution produces identical git structure on every run (given same tickets)

## Acceptance Criteria
- State machine can save epic-state.json atomically (write to temp, then rename)
- State machine can load state from epic-state.json for resumption
- State file includes epic metadata (id, branch, baseline_commit, started_at)
- State file includes all ticket states with git_info
- JSON schema validation on load
- Proper error handling for corrupted state files
- State file created in epic_dir/artifacts/epic-state.json

## Dependencies
- create-state-enums-and-models

## Files to Modify
- /Users/kit/Code/buildspec/epic/state_machine.py

## Additional Notes
Atomic saving is critical to prevent corrupted state files. Use the pattern:
1. Write to temporary file (e.g., epic-state.json.tmp)
2. Rename to epic-state.json (atomic on POSIX systems)

The state file format should be JSON for human readability and debugging. Include all information needed to resume:
- Epic metadata (id, branch, baseline_commit, started_at, epic_state)
- All tickets with their current state, git_info, timestamps
- Any failure reasons or blocking information

JSON schema validation on load ensures the state file is well-formed. If corrupted, the state machine should fail fast with a clear error message.
