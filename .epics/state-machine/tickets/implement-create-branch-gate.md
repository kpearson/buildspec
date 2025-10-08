# Implement Create Branch Gate

## Description
Implement CreateBranchGate to create git branch from correct base commit with stacking logic

## Dependencies
- create-gate-interface-and-protocol
- implement-git-operations-wrapper

## Acceptance Criteria
- [ ] CreateBranchGate calculates base commit deterministically
- [ ] First ticket (no dependencies) branches from epic baseline
- [ ] Ticket with single dependency branches from dependency's final commit (true stacking)
- [ ] Ticket with multiple dependencies finds most recent commit via git
- [ ] Creates branch with format "ticket/{ticket-id}"
- [ ] Pushes branch to remote
- [ ] Returns GateResult with metadata containing branch_name and base_commit
- [ ] Handles git errors gracefully
- [ ] Validates dependency is COMPLETED before using its final commit

## Files to Modify
- /Users/kit/Code/buildspec/epic/gates.py
