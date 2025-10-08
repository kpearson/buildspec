# Implement Fail Ticket API

## Description
Implement fail_ticket() public API method and _handle_ticket_failure helper

## Dependencies
- implement-state-machine-core

## Acceptance Criteria
- [ ] fail_ticket(ticket_id, reason) marks ticket as FAILED
- [ ] _handle_ticket_failure blocks all dependent tickets
- [ ] Blocked tickets transition to BLOCKED state with blocking_dependency field
- [ ] Critical ticket failure sets epic_state to FAILED
- [ ] Critical ticket failure triggers rollback if rollback_on_failure=True
- [ ] Non-critical ticket failure does not fail epic

## Files to Modify
- /Users/kit/Code/buildspec/epic/state_machine.py
