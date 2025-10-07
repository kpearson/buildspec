# add-no-live-updates-flag

## Description
Add --no-live-updates flag to execute-epic to disable git watching and use basic spinner

## Acceptance Criteria
- execute_epic command accepts --no-live-updates flag
- When flag is set, use basic spinner instead of git watching
- Default behavior is live updates enabled
- Flag is documented in command help text
- Useful for CI environments or when git polling overhead is undesirable

## Files to Modify
- /Users/kit/Code/buildspec/cli/commands/execute_epic.py

## Dependencies
- implement-git-commit-watching-for-execute-epic
