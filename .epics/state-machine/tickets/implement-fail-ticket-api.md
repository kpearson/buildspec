# implement-fail-ticket-api

## Description
Implement fail_ticket() public API method and _handle_ticket_failure helper

## Epic Context
This ticket implements the failure handling logic for the state machine. It defines how ticket failures cascade to dependent tickets and how critical failures affect the entire epic.

**Key Objectives**:
- Deterministic State Transitions: Failure handling is code-enforced, not LLM-driven
- Auditable Execution: All failures are logged with reasons

**Key Constraints**:
- Critical ticket failure fails the entire epic
- Non-critical ticket failure does not fail epic
- Dependent tickets are blocked when a dependency fails

## Acceptance Criteria
- fail_ticket(ticket_id, reason) marks ticket as FAILED
- _handle_ticket_failure blocks all dependent tickets
- Blocked tickets transition to BLOCKED state with blocking_dependency field
- Critical ticket failure sets epic_state to FAILED
- Critical ticket failure triggers rollback if rollback_on_failure=True
- Non-critical ticket failure does not fail epic

## Dependencies
- implement-state-machine-core

## Files to Modify
- /Users/kit/Code/buildspec/epic/state_machine.py

## Additional Notes
Failure handling has two public interfaces:

1. **fail_ticket(ticket_id, reason)**: Called by LLM or validation failure to explicitly mark a ticket as failed
2. **_handle_ticket_failure(ticket, reason)**: Private helper that handles failure cascade

Failure cascade logic:
1. Mark ticket as FAILED with reason
2. Find all tickets that depend on this ticket
3. Transition dependent tickets to BLOCKED state
4. Set blocking_dependency field to identify which dependency blocked them
5. If ticket is critical:
   - Set epic_state to FAILED
   - If rollback_on_failure configured, trigger git rollback
6. If ticket is non-critical:
   - Epic continues, blocked tickets stay BLOCKED
   - Epic can still succeed if non-blocked path exists

This ensures failures are handled deterministically and dependents cannot accidentally start work on a broken foundation.
