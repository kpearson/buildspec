# Deterministic ticket failure handling with cascading

**Ticket ID:** implement-failure-handling

**Critical:** true

**Dependencies:** core-state-machine, create-state-models

**Coordination Role:** Provides failure semantics and cascading for state machine

## Description

As a developer, I want deterministic ticket failure handling with cascading effects so that dependent tickets are blocked and critical failures trigger epic failure.

This ticket enhances _fail_ticket() and _handle_ticket_failure() methods in state_machine.py (ticket: core-state-machine) to implement failure semantics with blocking cascade. When a ticket fails, all dependent tickets must be blocked (cannot execute), and if the failed ticket is critical the epic must fail. Key logic to implement:
- _fail_ticket(ticket_id: str, reason: str): Get ticket, set ticket.failure_reason = reason, transition ticket to FAILED, call _handle_ticket_failure(ticket)
- _handle_ticket_failure(ticket: Ticket): Call _find_dependents(ticket.id) to get dependent ticket IDs, for each dependent if state not in [COMPLETED, FAILED] set dependent.blocking_dependency = ticket.id and transition to BLOCKED, if ticket.critical and epic_config.rollback_on_failure call _execute_rollback(), elif ticket.critical transition epic to FAILED, save state
- _find_dependents(ticket_id: str) -> List[str]: Iterate all tickets, return IDs where ticket_id in ticket.depends_on

## Acceptance Criteria

- Failed ticket marked with failure_reason
- All dependent tickets transitioned to BLOCKED state
- Blocked tickets record blocking_dependency field
- Critical ticket failure transitions epic to FAILED (if no rollback)
- Non-critical ticket failure allows independent tickets to continue executing
- Blocked tickets cannot transition to READY

## Testing

Unit tests for _find_dependents with various dependency graphs. Unit tests for _handle_ticket_failure with critical and non-critical tickets. Integration test with epic where ticket B depends on A, A fails, verify B blocked and C (independent) continues. Coverage: 90% minimum.

## Non-Goals

No retry logic, no partial recovery, no failure notifications, no manual intervention hooks.
