# implement-get-epic-status-api

## Description
Implement get_epic_status() public API method to return current epic state

## Epic Context
This method provides a read-only view of the epic's current state. It's used by the LLM orchestrator and CLI to understand the current execution status.

**Key Objectives**:
- LLM Interface Boundary: Clear contract for querying state
- Auditable Execution: Expose state for debugging and monitoring

**Key Constraints**:
- LLM agents interact with state machine via CLI commands only
- State file is private to state machine (this API is the read interface)

## Acceptance Criteria
- get_epic_status() returns dict with epic_state, tickets, stats
- Tickets dict includes state, critical, git_info for each ticket
- Stats include total, completed, in_progress, failed, blocked counts
- JSON serializable output

## Dependencies
- implement-state-machine-core

## Files to Modify
- /Users/kit/Code/buildspec/epic/state_machine.py

## Additional Notes
This method returns a comprehensive status dict:

```python
{
  "epic_id": "state-machine",
  "epic_state": "EXECUTING",
  "epic_branch": "state-machine",
  "baseline_commit": "abc123",
  "started_at": "2025-10-08T10:00:00",
  "tickets": {
    "ticket-1": {
      "state": "COMPLETED",
      "critical": true,
      "git_info": {
        "branch_name": "ticket/ticket-1",
        "base_commit": "abc123",
        "final_commit": "def456"
      },
      "started_at": "...",
      "completed_at": "..."
    },
    // ... more tickets
  },
  "stats": {
    "total": 23,
    "completed": 5,
    "in_progress": 1,
    "failed": 0,
    "blocked": 0,
    "pending": 12,
    "ready": 5
  }
}
```

This output is JSON serializable for easy consumption by CLI and LLM. It provides full visibility into epic progress without exposing the state file directly.
