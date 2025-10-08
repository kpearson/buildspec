# Progress UI Enhancement Spec

## Overview

Add visual progress indicators to buildspec CLI commands to provide user feedback during long-running Claude headless operations. Currently, users see no feedback while Claude is executing tasks, which can take minutes. This enhancement will use the existing `rich` library (already a dependency) to show spinners and status updates.

## Problem Statement

When running headless commands like `buildspec execute-epic` or `buildspec execute-ticket`, the CLI appears frozen with no feedback while Claude processes the request. Users cannot tell if:
- The command is still running
- What phase of execution is happening
- Whether the process has hung

This creates poor UX and uncertainty, especially for long-running operations.

## Goals

1. Provide visual feedback during Claude CLI subprocess execution
2. Show what phase of work is happening (building prompt, executing, waiting for response)
3. For `execute-epic`: Show live updates as tickets complete by watching git commits
4. Use existing `rich` library capabilities (no new dependencies)
5. Maintain clean output that doesn't interfere with final results
6. Support JSON output mode (progress UI should not interfere with JSON parsing)

## Non-Goals

- Interactive progress bars with percentage completion (Claude doesn't provide this data)
- Parsing Claude's streaming output (too complex, requires JSON stream parsing)
- Replacing or modifying Claude's own output

## Technical Design

### Rich Library Capabilities

We already depend on `rich>=13.0.0` which provides:
- `rich.spinner.Spinner` - Animated spinners with customizable text
- `rich.live.Live` - Live updating display context
- `rich.console.Console` - Already used throughout the CLI
- `rich.status.Status` - Higher-level spinner with status text

### Implementation Approach

**Option 1: Simple Spinner (Recommended)**
Use `rich.console.Console.status()` context manager:
- Simplest implementation
- Clean integration with existing Console usage
- Automatically cleans up when done
- Example: `with console.status("[bold green]Executing Claude...") as status:`

**Option 2: Live Updates**
Use `rich.live.Live` with custom renderables:
- More control over display
- Can show multi-line status
- Slightly more complex

**Option 3: Progress Bar**
Use `rich.progress.Progress`:
- Visual but misleading (we don't know % complete)
- Could show elapsed time as indeterminate progress
- Most complex implementation

### Recommended Phases to Show

1. **Building prompt** - Brief, often imperceptible
2. **Executing with Claude** - Main phase where spinner is valuable
3. **Complete** - Clean up spinner, show final result

### File Changes Needed

**cli/core/claude.py** - Update `ClaudeRunner.execute()`:
- Accept optional `Console` parameter
- Show spinner during `subprocess.run()` if console provided
- Handle spinner cleanup on completion/error

**cli/commands/*.py** - All command files:
- Pass `console` to `runner.execute()`
- Keep existing success/error message logic

### Example Implementation

```python
# In cli/core/claude.py
def execute(self, prompt: str, session_id: Optional[str] = None, 
            console: Optional[Console] = None) -> Tuple[int, str]:
    if session_id is None:
        session_id = str(uuid.uuid4())
    
    try:
        status_text = "[bold cyan]Executing with Claude...[/bold cyan]"
        
        if console:
            with console.status(status_text, spinner="dots") as status:
                result = subprocess.run(
                    ["claude", "-p", prompt, "--dangerously-skip-permissions", 
                     "--output-format=json", "--session-id", session_id],
                    cwd=self.context.cwd,
                    check=False,
                    text=True,
                    capture_output=True,
                )
        else:
            result = subprocess.run(
                ["claude", "-p", prompt, "--dangerously-skip-permissions", 
                 "--output-format=json", "--session-id", session_id],
                cwd=self.context.cwd,
                check=False,
                text=True,
                capture_output=True,
            )
        
        return result.returncode, session_id
    except FileNotFoundError as e:
        raise RuntimeError(
            "Claude CLI not found in PATH.\n"
            "Install Claude Code first: https://claude.com/claude-code"
        ) from e
```

```python
# In cli/commands/execute_epic.py (example)
# Just add console parameter:
exit_code, returned_session_id = runner.execute(prompt, session_id=session_id, console=console)
```

## Spinner Style Options

Rich provides several spinner styles. **Selected: `bouncingBar`**

**`bouncingBar`** characteristics:
- Pure ASCII characters: `[`, `]`, `=`, space
- Frames: `[    ]` → `[=   ]` → `[==  ]` → `[=== ]` → `[ ===]` → `[  ==]` → `[   =]`
- Maximum compatibility (works on all terminals, no Unicode needed)
- Clean, professional appearance
- No font/encoding issues

## Edge Cases

1. **Non-TTY environments** - Rich automatically detects and disables spinners
2. **JSON output mode** - Spinner writes to stderr, won't interfere with stdout JSON
3. **Ctrl+C interruption** - Rich context manager handles cleanup
4. **Error conditions** - Spinner auto-cleans up on exception

## Success Criteria

1. User sees spinner animation during Claude execution
2. Spinner disappears cleanly when complete
3. No interference with final output messages
4. No new dependencies added
5. Works in both interactive and non-interactive terminals

## Live Updates for execute-epic

### Challenge
Claude runs as a subprocess - we cannot directly see its internal progress. However, we CAN watch external indicators.

### Solution: Git Commit Watching
For `execute-epic` command, watch git commits in real-time to show ticket completion:

1. Get initial commit SHA before starting
2. Poll `git log` every 1-2 seconds during execution
3. When new commits appear, extract ticket info from commit messages
4. Update live display to show: `✓ Ticket: <ticket-name>`

### Implementation Approach

```python
# In execute-epic command
from rich.live import Live
from rich.table import Table
import subprocess
import time

def watch_git_commits(initial_sha, console):
    """Poll git log for new commits and yield ticket names."""
    while True:
        result = subprocess.run(
            ["git", "log", f"{initial_sha}..HEAD", "--oneline", "--reverse"],
            capture_output=True, text=True, check=False
        )
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                # Parse commit message for ticket name
                # Assuming format: "feat: implement user-auth (#123)"
                # Extract ticket name from commit message
                yield parse_ticket_from_commit(line)
        time.sleep(2)

def execute_with_live_updates(runner, prompt, session_id, console):
    # Get current HEAD
    initial_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True
    ).stdout.strip()
    
    # Create display table
    table = Table(show_header=False, box=None)
    completed_tickets = []
    
    with Live(table, console=console, refresh_per_second=2) as live:
        # Start Claude in background thread
        import threading
        result_container = {}
        
        def run_claude():
            result_container['exit_code'], result_container['session_id'] = \
                runner.execute(prompt, session_id=session_id)
        
        thread = threading.Thread(target=run_claude)
        thread.start()
        
        # Watch for commits while Claude runs
        while thread.is_alive():
            result = subprocess.run(
                ["git", "log", f"{initial_sha}..HEAD", "--oneline", "--reverse"],
                capture_output=True, text=True, check=False
            )
            
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                if len(lines) > len(completed_tickets):
                    # New commits detected
                    for line in lines[len(completed_tickets):]:
                        ticket_name = parse_ticket_from_commit(line)
                        completed_tickets.append(ticket_name)
                        table.add_row(f"[green]✓[/green] Ticket: {ticket_name}")
            
            time.sleep(2)
        
        thread.join()
        return result_container['exit_code'], result_container['session_id']
```

### Commit Message Parsing
Extract ticket name from commit messages. Patterns to look for:
- Look for ticket files referenced in commit
- Parse structured commit messages
- Extract from commit body (where session_id is stored)

### Fallback
If git watching fails or no commits detected:
- Fall back to simple spinner
- Show summary after completion from JSON output

## Future Enhancements (Out of Scope)

- Parse Claude's JSON stream output for real-time status updates (`--output-format=stream-json`)
- Show elapsed time counter
- Progress bars with percentage (X/Y tickets complete)
- Real-time log streaming from Claude output

## Testing Approach

1. Manual testing with all four commands
2. Test in TTY and non-TTY environments
3. Test with long-running operations
4. Verify clean output on success/failure
5. Test Ctrl+C interruption

## Estimated Complexity

### Basic Spinner (All Commands)
- **Effort**: Small (2-3 hours)
- **Risk**: Low (using existing library, additive change)
- **Files**: 5 files (claude.py + 4 command files)
- **Lines**: ~30 lines added/modified

### Live Git Updates (execute-epic only)
- **Effort**: Medium (4-6 hours)
- **Risk**: Medium (threading, git polling, parsing logic)
- **Files**: 2 files (execute_epic.py, potentially new utils module)
- **Lines**: ~100-150 lines added
- **Considerations**: 
  - Threading complexity
  - Git polling overhead
  - Commit message parsing reliability
  - Handling edge cases (no commits, errors, etc.)

## Dependencies

None - uses existing `rich>=13.0.0` dependency

## Open Questions

1. Should we show different spinner text for different commands?
   - **Decision**: Yes - "Creating epic...", "Creating tickets...", "Executing epic...", "Executing ticket..."

2. Should we add a `--quiet` flag to suppress spinner?
   - **Decision**: Not needed initially, Rich auto-detects non-TTY

3. Should we show elapsed time?
   - **Decision**: Out of scope for initial implementation

4. For execute-epic git watching: Should we show all commits or only ticket-related commits?
   - **Recommendation**: Show all commits, but highlight ticket completions differently

5. What happens if git polling fails or is too slow?
   - **Recommendation**: Fail gracefully to simple spinner mode

6. Should git watching be optional (flag to disable)?
   - **Recommendation**: Yes - add `--no-live-updates` flag for execute-epic
