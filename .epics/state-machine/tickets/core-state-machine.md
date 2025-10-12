# Self-driving EpicStateMachine for autonomous execution

**Ticket ID:** core-state-machine

**Critical:** true

**Dependencies:** create-state-models, create-git-operations, create-gate-interface, create-claude-builder

**Coordination Role:** Main orchestrator consuming all components to drive autonomous execution

## Description

As a developer, I want a self-driving EpicStateMachine that autonomously executes epics from start to finish so that epic coordination is deterministic, auditable, and does not depend on LLM reliability.

This ticket creates state_machine.py with the EpicStateMachine class containing the autonomous execute() method that drives the entire epic execution loop. This is the heart of the system that orchestrates ticket execution, state transitions, and validation gates. The state machine uses GitOperations (ticket: create-git-operations) for branch management, spawns ClaudeTicketBuilder (ticket: create-claude-builder) for ticket implementation, runs TransitionGate implementations (ticket: create-gate-interface) for validation, and persists state to epic-state.json atomically. The execution loop has two phases: Phase 1 executes tickets synchronously in dependency order, Phase 2 collapses all ticket branches into epic branch. Key methods to implement:
- __init__(epic_file: Path, resume: bool): Loads epic YAML, initializes or resumes from state file
- execute(): Main execution loop - Phase 1: while not all tickets completed, get ready tickets, execute next ticket; Phase 2: call _finalize_epic()
- _get_ready_tickets() -> List[Ticket]: Filters PENDING tickets, runs DependenciesMetGate, transitions to READY, returns sorted by priority
- _execute_ticket(ticket: Ticket): Calls _start_ticket, spawns ClaudeTicketBuilder, processes BuilderResult, calls _complete_ticket or _fail_ticket
- _start_ticket(ticket_id: str) -> Dict[str, Any]: Runs CreateBranchGate (creates branch), transitions to BRANCH_CREATED, runs LLMStartGate, transitions to IN_PROGRESS, returns branch info dict
- _complete_ticket(ticket_id, final_commit, test_status, acceptance_criteria) -> bool: Updates ticket with completion info, transitions to AWAITING_VALIDATION, runs ValidationGate, transitions to COMPLETED or FAILED
- _finalize_epic() -> Dict[str, Any]: Placeholder for collapse phase (implemented in ticket: implement-finalization-logic)
- _transition_ticket(ticket_id, new_state): Validates transition, updates ticket.state, calls _log_transition, calls _save_state
- _run_gate(ticket, gate) -> GateResult: Calls gate.check(), logs result, returns GateResult
- _save_state(): Serializes epic and ticket state to JSON, atomic write via temp file + rename
- _all_tickets_completed() -> bool: Returns True if all tickets in COMPLETED, BLOCKED, or FAILED states
- _has_active_tickets() -> bool: Returns True if any tickets in IN_PROGRESS or AWAITING_VALIDATION states

## Acceptance Criteria

- execute() method drives entire epic to completion without external intervention
- State transitions validated via gates before applying
- State persisted to epic-state.json atomically after each transition
- Synchronous execution enforced (LLMStartGate blocks if ticket active)
- Stacked branch strategy implemented via CreateBranchGate
- Ticket execution loop handles success and failure cases
- State machine creates epic branch if not exists

## Testing

Unit tests for each method with mocked dependencies (git, gates, builder). Integration test with simple 3-ticket epic using mocked builder to verify execution flow. Coverage: 85% minimum.

## Non-Goals

No parallel execution support, no complex error recovery (separate ticket: implement-failure-handling), no rollback logic yet (ticket: implement-rollback-logic), no resume logic yet (ticket: implement-resume-from-state), no finalization implementation (ticket: implement-finalization-logic).
