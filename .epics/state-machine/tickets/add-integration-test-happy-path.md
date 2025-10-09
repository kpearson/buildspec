# add-integration-test-happy-path

## Description
Add integration test for happy path (3 tickets, all succeed, finalize)

## Epic Context
This integration test validates the entire state machine flow end-to-end with a real git repository. It ensures the git strategy (stacked branches, squash merge) works correctly in practice.

**Git Strategy Summary**:
- Tickets execute synchronously (one at a time)
- Each ticket branches from previous ticket's final commit (true stacking)
- After all tickets complete, collapse all branches into epic branch (squash merge)

**Key Objectives**:
- Git Strategy Enforcement: Validate stacked branch creation and collapse work correctly
- Deterministic State Transitions: Validate state machine enforces all rules
- Epic execution produces identical git structure on every run

**Key Constraints**:
- Integration tests verify state machine enforces all invariants
- Epic execution produces identical git structure on every run
- Squash merge strategy for clean epic branch history

## Acceptance Criteria
- Test creates test epic with 3 sequential tickets
- Test initializes state machine
- Test executes all tickets synchronously
- Test validates stacked branches are created correctly
- Test validates tickets transition through all states
- Test validates finalize merges all tickets into epic branch
- Test validates epic branch is pushed to remote
- Test validates ticket branches are deleted
- Test uses real git repository (not mocked)

## Dependencies
- add-state-machine-unit-tests

## Files to Modify
- /Users/kit/Code/buildspec/tests/epic/test_integration.py

## Additional Notes
Happy path test flow:

1. **Setup**:
   - Create temporary git repository
   - Create test epic YAML with 3 tickets (A, B depends on A, C depends on B)
   - Initialize state machine

2. **Execute Ticket A**:
   - get_ready_tickets() returns [A]
   - start_ticket(A) creates branch from baseline
   - Simulate work: make commits on ticket/A branch
   - complete_ticket(A, final_commit) validates and completes
   - Verify A.state = COMPLETED

3. **Execute Ticket B**:
   - get_ready_tickets() returns [B]
   - start_ticket(B) creates branch from A's final_commit (stacking)
   - Verify B's base_commit = A's final_commit
   - Simulate work: make commits on ticket/B branch
   - complete_ticket(B) validates and completes

4. **Execute Ticket C**:
   - Similar to B, stacks on B's final_commit

5. **Finalize**:
   - finalize_epic() squash merges A, B, C into epic branch
   - Verify epic branch has 3 commits (one per ticket)
   - Verify ticket branches are deleted
   - Verify epic branch is pushed

This test validates the core happy path works end-to-end.
