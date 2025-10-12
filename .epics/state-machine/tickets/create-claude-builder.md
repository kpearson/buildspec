# ClaudeTicketBuilder for spawning Claude Code subprocess

**Ticket ID:** create-claude-builder

**Critical:** true

**Dependencies:** create-state-models

**Coordination Role:** Provides ticket implementation service to state machine via subprocess

## Description

As a state machine developer, I want a ClaudeTicketBuilder class that spawns Claude Code as a subprocess so that ticket implementation is delegated to Claude while the state machine retains control over coordination and validation.

This ticket creates claude_builder.py with the ClaudeTicketBuilder class that spawns Claude Code as a subprocess for individual ticket implementation. The state machine (ticket: core-state-machine) calls execute() method to spawn Claude, waits for completion (with 1 hour timeout), and receives BuilderResult with structured output (final commit SHA, test status, acceptance criteria). The builder is responsible for constructing the prompt that instructs Claude to implement the ticket and return JSON output. Key functions to implement:
- __init__(ticket_file: Path, branch_name: str, base_commit: str, epic_file: Path): Stores ticket context
- execute() -> BuilderResult: Spawns subprocess ["claude", "--prompt", prompt, "--mode", "execute-ticket", "--output-json"], waits up to 3600 seconds, captures stdout/stderr, returns BuilderResult with success/failure
- _build_prompt() -> str: Constructs instruction prompt including ticket file path, branch name, base commit, epic file path, workflow steps, output format requirements (JSON with final_commit, test_status, acceptance_criteria)
- _parse_output(stdout: str) -> Dict[str, Any]: Parses JSON object from stdout (finds {...} block in text, handles JSONDecodeError)

## Acceptance Criteria

- Subprocess spawned with correct CLI arguments
- Timeout enforced at 3600 seconds (raises BuilderResult with error)
- Structured JSON output parsed correctly from stdout
- Subprocess errors captured and returned in BuilderResult.error
- Prompt includes all necessary context (ticket, branch, epic, output requirements)
- BuilderResult model (from ticket: create-state-models) properly populated

## Testing

Unit tests with mocked subprocess.run for success case (valid JSON), failure case (non-zero exit), timeout case (TimeoutExpired), and parsing failure case (invalid JSON). Integration test with simple echo subprocess that returns mock JSON. Coverage: 90% minimum.

## Non-Goals

No actual Claude Code integration testing (use mock subprocess), no retry logic, no streaming output, no interactive prompts, no builder state persistence - this is subprocess spawning only.
