# add-spinner-to-create-epic-command

## Description
Pass console to ClaudeRunner in create-epic command to show spinner

## Acceptance Criteria
- create_epic command passes console parameter to runner.execute()
- Existing success/error message logic is preserved
- Spinner shows while Claude creates epic
- No interference with final output messages

## Files to Modify
- /Users/kit/Code/buildspec/cli/commands/create_epic.py

## Dependencies
- add-console-parameter-to-claude-runner
