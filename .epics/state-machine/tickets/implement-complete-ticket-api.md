# implement-complete-ticket-api

## Description

Implement complete_ticket() public API method in state machine

## Epic Context

This public API method validates and completes a ticket after the LLM has
finished the work. It runs validation gates to ensure the work meets
requirements before transitioning to COMPLETED.

**Key Objectives**:

- Validation Gates: Automated checks before allowing state transitions
- LLM Interface Boundary: Clear contract for reporting completion
- Deterministic State Transitions: Gates enforce quality before completion

**Key Constraints**:

- Validation gates automatically verify LLM work before accepting state
  transitions
- Critical tickets must pass all validation
- State machine logs all transitions and gate checks

## Acceptance Criteria

- complete_ticket(ticket_id, final_commit, test_suite_status,
  acceptance_criteria) validates and transitions ticket
- Transitions IN_PROGRESS → AWAITING_VALIDATION → COMPLETED (if validation
  passes)
- Transitions to FAILED if validation fails
- Runs ValidationGate to verify work
- Updates ticket with final_commit, test_suite_status, acceptance_criteria
- Marks ticket.completed_at timestamp
- Returns True if validation passed, False if failed
- Calls \_handle_ticket_failure if validation fails

## Dependencies

- implement-state-machine-core
- implement-validation-gate

## Files to Modify

- /Users/kit/Code/buildspec/epic/state_machine.py

## Additional Notes

This method is called by the LLM after completing work on a ticket. The LLM
provides:

- final_commit: the SHA of the final commit on the ticket branch
- test_suite_status: "passing", "failing", or "skipped"
- acceptance_criteria: list of acceptance criteria with met status

The method orchestrates completion:

1. **Validate State**: Ensure ticket is in IN_PROGRESS
2. **Update Ticket**: Store final_commit, test_suite_status, acceptance_criteria
3. **Await Validation** (IN_PROGRESS → AWAITING_VALIDATION):
   - Transition to AWAITING_VALIDATION state
   - Persist state
4. **Validate Work**:
   - Run ValidationGate to check all requirements
   - If passed: transition to COMPLETED, mark completed_at, persist
   - If failed: call \_handle_ticket_failure, transition to FAILED
5. **Return Result**: Boolean indicating success/failure

The AWAITING_VALIDATION state is important for debugging - it shows the ticket
is waiting for automated validation checks.
