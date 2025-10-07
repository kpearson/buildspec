# add-commit-message-parsing-utility

## Description
Create utility function to parse ticket names from git commit messages

## Acceptance Criteria
- Function extracts ticket name from commit message
- Handles multiple commit message formats
- Returns ticket name or fallback to commit SHA
- Parses structured commit messages (feat:, fix:, etc.)
- Can extract from commit body if needed
- Well-tested with various commit message patterns

## Files to Modify
- /Users/kit/Code/buildspec/cli/commands/execute_epic.py

## Dependencies
- implement-git-commit-watching-for-execute-epic
