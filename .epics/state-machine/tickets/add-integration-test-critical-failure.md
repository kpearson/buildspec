# add-integration-test-critical-failure

## Description
Add integration test for critical ticket failure with rollback

## Epic Context
This test validates that critical ticket failures properly fail the epic and block dependent tickets, as designed. Critical tickets are those that the entire epic depends on.

**Key Objectives**:
- Deterministic State Transitions: Validate failure handling is code-enforced
- Auditable Execution: Validate failures are logged correctly

**Key Constraints**:
- Critical ticket failure fails the entire epic
- Dependent tickets are blocked when a dependency fails
- Integration tests verify state machine enforces all invariants

## Acceptance Criteria
- Test creates epic with critical ticket that fails
- Test verifies epic state transitions to FAILED
- Test verifies dependent tickets are BLOCKED
- Test verifies rollback is triggered if configured
- Test verifies state is preserved correctly

## Dependencies
- add-integration-test-happy-path

## Files to Modify
- /Users/kit/Code/buildspec/tests/epic/test_integration.py

## Additional Notes
Critical failure test flow:

1. **Setup**:
   - Create test epic with tickets: A (critical), B depends on A, C depends on B
   - Initialize state machine

2. **Execute and Fail Ticket A**:
   - start_ticket(A)
   - Simulate work but introduce failure
   - complete_ticket(A) or fail_ticket(A) with failure reason
   - Verify validation fails (e.g., tests failing)
   - Verify A.state = FAILED

3. **Verify Failure Cascade**:
   - Verify B.state = BLOCKED (dependency A failed)
   - Verify C.state = BLOCKED (transitive dependency A failed)
   - Verify B.blocking_dependency = "A"
   - Verify C.blocking_dependency = "A" (or "B")

4. **Verify Epic Failed**:
   - Verify epic_state = FAILED
   - Verify epic cannot be finalized

5. **Verify Rollback (if configured)**:
   - If rollback_on_failure=True, verify git rollback occurs
   - If rollback_on_failure=False, verify state preserved for debugging

This test ensures critical failures are handled correctly and the epic stops execution appropriately.
