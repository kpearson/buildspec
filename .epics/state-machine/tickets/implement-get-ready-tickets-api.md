# Implement Get Ready Tickets API

## Description
Implement get_ready_tickets() public API method in state machine

## Dependencies
- implement-state-machine-core
- implement-dependencies-met-gate

## Acceptance Criteria
- [ ] get_ready_tickets() returns list of tickets in READY state
- [ ] Automatically transitions PENDING tickets to READY if dependencies met
- [ ] Uses DependenciesMetGate to check dependencies
- [ ] Returns tickets sorted by priority (critical first, then by dependency depth)
- [ ] Returns empty list if no tickets ready

## Files to Modify
- /Users/kit/Code/buildspec/epic/state_machine.py
