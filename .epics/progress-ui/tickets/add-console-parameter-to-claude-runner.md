# add-console-parameter-to-claude-runner

## Description
Update ClaudeRunner.execute() to accept optional Console parameter for spinner support

## Acceptance Criteria
- ClaudeRunner.execute() accepts optional console parameter
- When console is provided, spinner shows during subprocess.run()
- Spinner text is "[bold cyan]Executing with Claude...[/bold cyan]"
- Spinner style is "bouncingBar" for ASCII compatibility
- Spinner automatically cleans up on completion or error
- When console is None, behavior is unchanged (backward compatible)
- Spinner uses console.status() context manager from rich

## Files to Modify
- /Users/kit/Code/buildspec/cli/core/claude.py

## Dependencies
None
