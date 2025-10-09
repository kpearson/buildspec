# implement-create-branch-gate

## Description

Implement CreateBranchGate to create git branch from correct base commit with
stacking logic

## Epic Context

This gate implements the core git stacking strategy of the epic. It calculates
the correct base commit for a ticket's branch based on its dependencies and
creates the branch.

**Git Strategy Summary**:

- Tickets execute synchronously (one at a time)
- Each ticket branches from previous ticket's final commit (true stacking)
- Epic branch stays at baseline during execution
- First ticket (no dependencies) branches from epic baseline

**Key Objectives**:

- Git Strategy Enforcement: Stacked branch creation, base commit calculation,
  and merge order handled by code
- Deterministic State Transitions: Python code enforces state machine rules

**Key Constraints**:

- Git operations (branch creation, base commit calculation, merging) are
  deterministic and tested
- Epic execution produces identical git structure on every run (given same
  tickets)

## Acceptance Criteria

- CreateBranchGate calculates base commit deterministically
- First ticket (no dependencies) branches from epic baseline
- Ticket with single dependency branches from dependency's final commit (true
  stacking)
- Ticket with multiple dependencies finds most recent commit via git
- Creates branch with format "ticket/{ticket-id}"
- Pushes branch to remote
- Returns GateResult with metadata containing branch_name and base_commit
- Handles git errors gracefully
- Validates dependency is COMPLETED before using its final commit

## Dependencies

- create-gate-interface-and-protocol
- implement-git-operations-wrapper

## Files to Modify

- /Users/kit/Code/buildspec/epic/gates.py

## Additional Notes

Base commit calculation logic:

1. No dependencies: base = epic baseline_commit
2. Single dependency: base = dependency.git_info.final_commit
3. Multiple dependencies: base =
   find_most_recent_commit(all_dependency_final_commits)

The gate must validate that dependencies are COMPLETED and have a final_commit
before using them as a base. This prevents attempting to branch from a
non-existent commit.

Branch naming convention: "ticket/{ticket-id}" ensures consistent, predictable
branch names that can be easily identified and cleaned up later.

After creating the branch, it must be pushed to remote immediately to make it
available for the LLM worker.
