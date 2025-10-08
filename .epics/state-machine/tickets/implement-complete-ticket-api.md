# Implement Complete Ticket API

## Description
Implement complete_ticket() public API method in state machine

## Dependencies
- implement-state-machine-core
- implement-validation-gate

## Acceptance Criteria
- [ ] complete_ticket(ticket_id, final_commit, test_suite_status, acceptance_criteria) validates and transitions ticket
- [ ] Transitions IN_PROGRESS → AWAITING_VALIDATION → COMPLETED (if validation passes)
- [ ] Transitions to FAILED if validation fails
- [ ] Runs ValidationGate to verify work
- [ ] Updates ticket with final_commit, test_suite_status, acceptance_criteria
- [ ] Marks ticket.completed_at timestamp
- [ ] Returns True if validation passed, False if failed
- [ ] Calls _handle_ticket_failure if validation fails

## Files to Modify
- /Users/kit/Code/buildspec/epic/state_machine.py
