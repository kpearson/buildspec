# Failure scenario integration tests

**Ticket ID:** add-failure-scenario-integration-tests

**Critical:** true

**Dependencies:** add-happy-path-integration-test, implement-failure-handling, implement-rollback-logic

**Coordination Role:** Validates failure handling semantics with real scenarios

## Description

As a developer, I want integration tests for failure scenarios (critical failures with rollback, non-critical failures with blocking) so that I can verify error handling and cascading work correctly.

This ticket creates tests/integration/epic/test_failure_scenarios.py with multiple test cases covering failure semantics. Uses state machine (ticket: core-state-machine), failure handling (ticket: implement-failure-handling), and rollback logic (ticket: implement-rollback-logic). Tests use real git operations and mocked ClaudeTicketBuilder that returns failures for specific tickets. Key test scenarios:
- test_critical_failure_triggers_rollback(): Epic with rollback_on_failure=true, ticket A (critical) fails, verify rollback executed (all branches deleted, epic ROLLED_BACK)
- test_noncritical_failure_blocks_dependents(): Ticket B (non-critical) fails, ticket D depends on B, verify D blocked but independent tickets continue
- test_diamond_dependency_partial_execution(): Diamond (A → B, A → C, B+C → D), B fails, verify C completes, D blocked, A completed
- test_multiple_independent_with_failure(): 3 independent tickets, middle one fails, verify other two complete, epic finalized without failed ticket

## Acceptance Criteria

- Critical failure test verifies rollback executed and branches deleted
- Non-critical failure test verifies blocking cascade to dependents
- Diamond dependency test verifies partial execution (C completes, D blocked)
- All tests use real git operations
- All tests pass consistently

## Testing

These ARE the integration tests. Run them to verify failure handling. Expected runtime: <10 seconds total.

## Non-Goals

No retry scenarios, no manual recovery intervention, no partial rollback.
