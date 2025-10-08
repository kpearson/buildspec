# Progress UI Enhancement Epic

Add visual progress indicators to CLI commands during Claude headless operations

## Epic Overview

Currently, users see no feedback while Claude is executing tasks, which can take minutes. When running headless commands like `buildspec execute-epic` or `buildspec execute-ticket`, the CLI appears frozen with no feedback. Users cannot tell if the command is still running, what phase of execution is happening, or whether the process has hung.

This epic uses the existing `rich` library (already a dependency) to show spinners and status updates during long-running operations.

## Implementation Strategy

The implementation will be in two phases:
1. Basic spinner for all commands (tickets 1-5)
2. Live git commit watching for execute-epic (tickets 6-8)

## Constraints

- Must use existing rich>=13.0.0 dependency (no new dependencies)
- Spinner must not interfere with JSON output mode (write to stderr)
- Must work in both TTY and non-TTY environments (Rich auto-detects)
- Cannot parse Claude's streaming output (too complex)
- Must handle Ctrl+C interruption gracefully
- Selected spinner style is "bouncingBar" for maximum ASCII compatibility

## Success Criteria

- All CLI commands show visual feedback during Claude execution
- Users can see what phase of work is happening
- For execute-epic: Live updates show tickets completing in real-time
- Clean output that doesn't interfere with final results
- JSON output mode continues to work correctly

```toml
[epic]
name = "progress-ui"
description = "Add visual progress indicators to CLI commands during Claude headless operations"

[[tickets]]
id = "add-console-parameter-to-claude-runner"
path = "tickets/add-console-parameter-to-claude-runner.md"
critical = true
depends_on = []

[[tickets]]
id = "add-spinner-to-create-epic-command"
path = "tickets/add-spinner-to-create-epic-command.md"
critical = true
depends_on = ["add-console-parameter-to-claude-runner"]

[[tickets]]
id = "add-spinner-to-create-tickets-command"
path = "tickets/add-spinner-to-create-tickets-command.md"
critical = true
depends_on = ["add-console-parameter-to-claude-runner"]

[[tickets]]
id = "add-spinner-to-execute-ticket-command"
path = "tickets/add-spinner-to-execute-ticket-command.md"
critical = true
depends_on = ["add-console-parameter-to-claude-runner"]

[[tickets]]
id = "add-basic-spinner-to-execute-epic-command"
path = "tickets/add-basic-spinner-to-execute-epic-command.md"
critical = true
depends_on = ["add-console-parameter-to-claude-runner"]

[[tickets]]
id = "implement-git-commit-watching-for-execute-epic"
path = "tickets/implement-git-commit-watching-for-execute-epic.md"
critical = true
depends_on = ["add-basic-spinner-to-execute-epic-command"]

[[tickets]]
id = "add-commit-message-parsing-utility"
path = "tickets/add-commit-message-parsing-utility.md"
critical = false
depends_on = ["implement-git-commit-watching-for-execute-epic"]

[[tickets]]
id = "add-no-live-updates-flag"
path = "tickets/add-no-live-updates-flag.md"
critical = false
depends_on = ["implement-git-commit-watching-for-execute-epic"]
```

## Ticket Summary

### Phase 1: Basic Spinner (Tickets 1-5)
1. **add-console-parameter-to-claude-runner** - Foundation: Update ClaudeRunner to accept Console parameter
2. **add-spinner-to-create-epic-command** - Add spinner to create-epic command
3. **add-spinner-to-create-tickets-command** - Add spinner to create-tickets command
4. **add-spinner-to-execute-ticket-command** - Add spinner to execute-ticket command
5. **add-basic-spinner-to-execute-epic-command** - Add basic spinner to execute-epic command

### Phase 2: Live Git Updates (Tickets 6-8)
6. **implement-git-commit-watching-for-execute-epic** - Replace basic spinner with live git commit watching
7. **add-commit-message-parsing-utility** - Create utility to parse ticket names from commit messages
8. **add-no-live-updates-flag** - Add flag to disable git watching

## Execution Plan

```
Phase 1 (Parallel after ticket 1):
  add-console-parameter-to-claude-runner (critical)
    ├── add-spinner-to-create-epic-command (critical, parallel)
    ├── add-spinner-to-create-tickets-command (critical, parallel)
    ├── add-spinner-to-execute-ticket-command (critical, parallel)
    └── add-basic-spinner-to-execute-epic-command (critical, parallel)

Phase 2 (Sequential):
  add-basic-spinner-to-execute-epic-command
    └── implement-git-commit-watching-for-execute-epic (critical)
        ├── add-commit-message-parsing-utility (non-critical, parallel)
        └── add-no-live-updates-flag (non-critical, parallel)
```

## Technical Notes

- Uses rich.console.Console.status() context manager for spinners
- Spinner style: "bouncingBar" (pure ASCII: `[====  ]`)
- Git watching polls every 2 seconds during epic execution
- Threading handles Claude subprocess while watching git commits
- Fallback to basic spinner if git watching fails
