# create-epic-cli-commands

## Description

Create CLI commands for state machine API (status, start-ticket,
complete-ticket, fail-ticket, finalize)

## Epic Context

These CLI commands provide the interface between the LLM orchestrator and the
state machine. They are the only way the LLM can interact with the state
machine, enforcing the boundary between coordinator (state machine) and worker
(LLM).

**Key Objectives**:

- LLM Interface Boundary: Clear contract between state machine (coordinator) and
  LLM (worker)
- Auditable Execution: All LLM interactions with state machine go through logged
  CLI commands

**Key Constraints**:

- LLM agents interact with state machine via CLI commands only (no direct state
  file manipulation)
- All commands output JSON for LLM consumption

## Acceptance Criteria

- Click command group 'buildspec epic' with subcommands
- epic status <epic_file> shows epic status JSON
- epic status <epic_file> --ready shows ready tickets JSON
- epic start-ticket <epic_file> <ticket_id> creates branch and returns info JSON
- epic complete-ticket <epic_file> <ticket_id> --final-commit --test-status
  --acceptance-criteria validates and returns result JSON
- epic fail-ticket <epic_file> <ticket_id> --reason marks ticket failed
- epic finalize <epic_file> collapses tickets and pushes epic branch
- All commands output JSON for LLM consumption
- Error handling with clear messages and non-zero exit codes
- Commands are in buildspec/cli/epic_commands.py

## Dependencies

- implement-get-epic-status-api
- implement-get-ready-tickets-api
- implement-start-ticket-api
- implement-complete-ticket-api
- implement-fail-ticket-api
- implement-finalize-epic-api

## Files to Modify

- /Users/kit/Code/buildspec/cli/epic_commands.py

## Additional Notes

Each command wraps a state machine API method and outputs JSON:

**epic status <epic_file>**:

- Calls get_epic_status()
- Outputs full status JSON

**epic status <epic_file> --ready**:

- Calls get_ready_tickets()
- Outputs array of ready tickets

**epic start-ticket <epic_file> <ticket_id>**:

- Calls start_ticket(ticket_id)
- Outputs: {"branch_name": "...", "base_commit": "...", "ticket_file": "...",
  "epic_file": "..."}

**epic complete-ticket <epic_file> <ticket_id> --final-commit <sha>
--test-status <status> --acceptance-criteria <json>**:

- Calls complete_ticket(ticket_id, final_commit, test_status,
  acceptance_criteria)
- Outputs: {"success": true/false, "ticket_id": "...", "state": "..."}

**epic fail-ticket <epic_file> <ticket_id> --reason <reason>**:

- Calls fail_ticket(ticket_id, reason)
- Outputs: {"ticket_id": "...", "state": "FAILED", "reason": "..."}

**epic finalize <epic_file>**:

- Calls finalize_epic()
- Outputs: {"success": true, "epic_branch": "...", "merge_commits": [...],
  "pushed": true}

All commands should catch exceptions and output error JSON with non-zero exit
codes.
