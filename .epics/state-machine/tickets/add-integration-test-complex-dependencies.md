# add-integration-test-complex-dependencies

## Description
Add integration test for diamond dependency graph

## Epic Context
This test validates the base commit calculation for tickets with multiple dependencies - a critical part of the stacked branch strategy. When a ticket has multiple dependencies, the state machine must find the most recent commit across all dependencies to use as the base.

**Git Strategy Context**:
- Ticket with multiple dependencies finds most recent commit via git
- Base commit calculation must be deterministic

**Key Objectives**:
- Git Strategy Enforcement: Validate base commit calculation for complex dependencies
- Deterministic State Transitions: Same dependency graph produces same git structure

**Key Constraints**:
- Git operations (base commit calculation) are deterministic and tested
- Epic execution produces identical git structure on every run

## Acceptance Criteria
- Test creates epic with diamond dependencies (A, B depends on A, C depends on A, D depends on B+C)
- Test verifies base commit calculation for ticket with multiple dependencies
- Test verifies execution order respects dependencies
- Test validates all tickets complete and merge correctly

## Dependencies
- add-integration-test-happy-path

## Files to Modify
- /Users/kit/Code/buildspec/tests/epic/test_integration.py

## Additional Notes
Diamond dependency test flow:

1. **Setup**:
   - Create epic with diamond dependency graph:
     ```
         A
        / \
       B   C
        \ /
         D
     ```
   - A: no dependencies
   - B: depends on A
   - C: depends on A
   - D: depends on B and C

2. **Execute A**:
   - start_ticket(A) branches from baseline
   - Complete A with final_commit = commit_A

3. **Execute B and C**:
   - Both branch from commit_A (A's final_commit)
   - B completes with final_commit = commit_B
   - C completes with final_commit = commit_C

4. **Execute D (Complex Case)**:
   - D depends on both B and C
   - start_ticket(D) must calculate base commit from [commit_B, commit_C]
   - Uses find_most_recent_commit to determine which is newer
   - Branches from the most recent commit
   - Verify D's base_commit is either commit_B or commit_C (whichever is newer)

5. **Finalize**:
   - All tickets merge successfully in topological order
   - Epic branch has 4 commits

This test validates the complex case of multiple dependencies and ensures the git strategy handles it deterministically.
