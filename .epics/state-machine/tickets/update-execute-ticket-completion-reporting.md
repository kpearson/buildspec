# update-execute-ticket-completion-reporting

## Description
Update execute-ticket.md to report completion to state machine API

## Epic Context
This ticket updates the execute-ticket instructions for sub-agents spawned by the orchestrator. Sub-agents now report their completion status back to the orchestrator, who forwards it to the state machine via CLI.

**Key Objectives**:
- LLM Interface Boundary: Clear contract for reporting work completion
- Validation Gates: Sub-agents report all data needed for validation

**Key Constraints**:
- LLM agents interact with state machine via CLI commands only (orchestrator does this, not sub-agent)
- Validation gates automatically verify LLM work before accepting state transitions

## Acceptance Criteria
- execute-ticket.md instructs sub-agent to report final commit SHA
- Documents how to report test suite status
- Documents how to report acceptance criteria completion
- Shows how to call complete-ticket API
- Shows how to call fail-ticket API on errors
- Maintains existing ticket implementation instructions

## Dependencies
- create-epic-cli-commands

## Files to Modify
- /Users/kit/Code/buildspec/.claude/prompts/execute-ticket.md

## Additional Notes
The sub-agent (execute-ticket) flow is:

**During Execution**:
1. Receives ticket context from orchestrator
2. Works on ticket branch (branch already created by state machine)
3. Implements features, runs tests, validates acceptance criteria
4. Does NOT merge or modify epic branch

**On Completion**:
Sub-agent reports back to orchestrator:
```json
{
  "final_commit": "abc123def456...",
  "test_suite_status": "passing",  // or "failing" or "skipped"
  "acceptance_criteria": [
    {"criterion": "...", "met": true},
    {"criterion": "...", "met": true}
  ]
}
```

**On Failure**:
Sub-agent reports back to orchestrator:
```json
{
  "error": "description of failure",
  "reason": "why ticket failed"
}
```

The orchestrator then calls the appropriate state machine API:
- Success: `buildspec epic complete-ticket ...`
- Failure: `buildspec epic fail-ticket ...`

The sub-agent does NOT call these CLI commands directly - it reports to the orchestrator, who coordinates with the state machine.
