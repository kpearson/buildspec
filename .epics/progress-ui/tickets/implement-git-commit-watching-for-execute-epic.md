# implement-git-commit-watching-for-execute-epic

## Description
Replace basic spinner with live git commit watching to show ticket completion in real-time

## Acceptance Criteria
- Get initial git commit SHA before starting Claude execution
- Poll git log every 2 seconds during execution using threading
- When new commits appear, parse ticket name from commit message
- Update live display showing completed tickets with checkmarks
- Use rich.live.Live with table for multi-line status display
- Fall back to basic spinner if git watching fails
- Handle edge cases (no commits, git errors, non-git directory)
- Threading handles Claude subprocess in background
- Clean cleanup on completion or error

## Files to Modify
- /Users/kit/Code/buildspec/cli/commands/execute_epic.py

## Dependencies
- add-basic-spinner-to-execute-epic-command
