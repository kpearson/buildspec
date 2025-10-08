# add-basic-spinner-to-execute-epic-command

## Description
Add basic spinner to execute-epic command (foundation for live updates)

## Acceptance Criteria
- execute_epic command passes console parameter to runner.execute()
- Basic spinner shows while Claude executes epic
- Existing success/error message logic is preserved
- No interference with final output messages
- Lays groundwork for live git updates (next ticket)

## Files to Modify
- /Users/kit/Code/buildspec/cli/commands/execute_epic.py

## Dependencies
- add-console-parameter-to-claude-runner
