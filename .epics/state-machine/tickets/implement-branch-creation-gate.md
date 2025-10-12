# CreateBranchGate for stacked branch creation

**Ticket ID:** implement-branch-creation-gate

**Critical:** true

**Dependencies:** create-gate-interface, create-git-operations, create-state-models

**Coordination Role:** Enforces stacked branch strategy and deterministic base commit calculation

## Description

As a state machine developer, I want a CreateBranchGate that creates stacked git branches from deterministically calculated base commits so that each ticket builds on previous work and the git history reflects dependency structure.

This ticket creates the CreateBranchGate class in gates.py implementing the TransitionGate protocol (ticket: create-gate-interface). The state machine (ticket: core-state-machine) runs this gate during READY → BRANCH_CREATED transition (in _start_ticket method). The gate calculates the correct base commit using the stacked branch strategy, creates the branch using GitOperations (ticket: create-git-operations), and pushes it to remote. Key functions to implement:
- check(ticket: Ticket, context: EpicContext) -> GateResult: Calls _calculate_base_commit, calls context.git.create_branch(f"ticket/{ticket.id}", base_commit), calls context.git.push_branch, returns GateResult(passed=True, metadata={"branch_name": ..., "base_commit": ...}), catches GitError and returns GateResult(passed=False, reason=str(e))
- _calculate_base_commit(ticket: Ticket, context: EpicContext) -> str: If no dependencies return context.epic_baseline_commit (first ticket branches from epic baseline), if single dependency return dep.git_info.final_commit (stacked branch), if multiple dependencies get list of final commits and return context.git.find_most_recent_commit(dep_commits) (handles diamond dependencies)

## Acceptance Criteria

- First ticket (no dependencies) branches from epic baseline commit
- Tickets with single dependency branch from that dependency's final commit (true stacking)
- Tickets with multiple dependencies branch from most recent dependency final commit
- Branch created with name format "ticket/{ticket-id}"
- Branch pushed to remote
- Returns branch info in GateResult metadata
- Raises error if dependency missing final_commit

## Testing

Unit tests for _calculate_base_commit with various dependency graphs (no deps, single dep, multiple deps, diamond). Unit tests for check() with mocked git operations. Integration tests with real git repository creating stacked branches. Coverage: 90% minimum.

## Non-Goals

No worktrees, no local-only branches, no branch naming customization, no merge conflict detection (happens later).
