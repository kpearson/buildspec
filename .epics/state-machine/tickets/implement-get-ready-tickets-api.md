# implement-get-ready-tickets-api

## Description
Implement get_ready_tickets() public API method in state machine

## Epic Context
This public API method provides the LLM orchestrator with a list of tickets that are ready to be started. It automatically transitions PENDING tickets to READY when their dependencies are met.

**Key Objectives**:
- LLM Interface Boundary: Clear contract between state machine (coordinator) and LLM (worker)
- Deterministic State Transitions: Python code enforces state machine rules

**Key Constraints**:
- LLM agents interact with state machine via CLI commands only
- Validation gates automatically verify conditions before accepting state transitions

## Acceptance Criteria
- get_ready_tickets() returns list of tickets in READY state
- Automatically transitions PENDING tickets to READY if dependencies met
- Uses DependenciesMetGate to check dependencies
- Returns tickets sorted by priority (critical first, then by dependency depth)
- Returns empty list if no tickets ready

## Dependencies
- implement-state-machine-core
- implement-dependencies-met-gate

## Files to Modify
- /Users/kit/Code/buildspec/epic/state_machine.py

## Additional Notes
This method is called by the LLM orchestrator to determine which tickets can be started next. It performs two functions:

1. **Proactive Transition**: Checks all PENDING tickets and transitions them to READY if their dependencies are COMPLETED (using DependenciesMetGate)

2. **Return Ready List**: Returns all tickets currently in READY state, sorted by priority

Sorting logic:
- Critical tickets before non-critical tickets
- Within same criticality, tickets with deeper dependency chains first (they're on the critical path)

This method enables the synchronous execution loop: orchestrator calls get_ready_tickets(), picks first ticket, starts it, waits for completion, repeats.
