# LLMStartGate for synchronous execution enforcement

**Ticket ID:** implement-llm-start-gate

**Critical:** true

**Dependencies:** create-gate-interface, create-state-models

**Coordination Role:** Enforces synchronous execution constraint for state machine

## Description

As a state machine developer, I want an LLMStartGate that enforces synchronous ticket execution so that only one Claude builder runs at a time, preventing concurrent state updates and git conflicts.

This ticket creates the LLMStartGate class in gates.py implementing the TransitionGate protocol (ticket: create-gate-interface). The state machine (ticket: core-state-machine) runs this gate during BRANCH_CREATED → IN_PROGRESS transition (in _start_ticket method after CreateBranchGate). The gate counts how many tickets are currently active (IN_PROGRESS or AWAITING_VALIDATION) and blocks if count >= 1, enforcing synchronous execution. Key function to implement:
- check(ticket: Ticket, context: EpicContext) -> GateResult: Count tickets in context.tickets where state in [TicketState.IN_PROGRESS, TicketState.AWAITING_VALIDATION], if count >= 1 return GateResult(passed=False, reason="Another ticket in progress (synchronous execution only)"), verify ticket branch exists on remote via context.git.branch_exists_remote(ticket.git_info.branch_name), return GateResult(passed=True) if checks pass

## Acceptance Criteria

- Blocks ticket start if ANY ticket is IN_PROGRESS
- Blocks ticket start if ANY ticket is AWAITING_VALIDATION
- Allows ticket start if NO tickets are active
- Verifies ticket branch exists on remote before allowing start
- Returns clear failure reason if blocked

## Testing

Unit tests with mock EpicContext containing various active ticket counts: no active (should pass), one IN_PROGRESS (should fail), one AWAITING_VALIDATION (should fail), multiple active (should fail). Test branch existence check with mocked git operations. Coverage: 100%.

## Non-Goals

No concurrency control beyond simple count check, no configurable concurrency limit (hardcoded to 1), no queuing or scheduling logic.
