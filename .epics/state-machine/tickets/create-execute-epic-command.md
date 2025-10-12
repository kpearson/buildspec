# CLI command for executing epics

**Ticket ID:** create-execute-epic-command

**Critical:** false

**Dependencies:** core-state-machine

**Coordination Role:** User-facing entry point that drives state machine execution

## Description

As a user, I want a simple CLI command "buildspec execute-epic" that starts autonomous epic execution so that I can run epics without manual coordination.

This ticket creates cli/commands/execute_epic.py with the execute_epic() function registered as a Click command. The command instantiates EpicStateMachine (ticket: core-state-machine) and calls execute() method, displaying progress and results using rich console. Key components to implement:
- execute_epic(epic_file: Path, resume: bool = False): Click command with @click.command decorator, validates epic_file exists and is YAML, creates EpicStateMachine(epic_file, resume), calls state_machine.execute() in try/except, displays progress during execution, catches exceptions and displays error messages, returns exit code 0 on success or 1 on failure
- Progress display: Use rich console to show ticket progress (ticket ID, state transitions), epic state changes, completion summary
- Error handling: Catch StateTransitionError, GitError, FileNotFoundError and display clear messages

## Acceptance Criteria

- Command registered in CLI as "buildspec execute-epic"
- Epic file path validated (exists, is file, has .epic.yaml extension)
- Resume flag supported (--resume)
- Progress displayed during execution (ticket starts, completions, state transitions)
- Errors displayed with clear messages and troubleshooting hints
- Exit code 0 on success, 1 on failure
- Help text explains command usage

## Testing

Unit tests with mocked EpicStateMachine for success and failure cases. Integration tests with fixture epics (simple 1-ticket epic). Coverage: 85% minimum.

## Non-Goals

No interactive prompts, no status polling commands, no epic cancellation (Ctrl-C stops execution), no progress bar (simple text updates).
