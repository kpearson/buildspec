# Epic finalization and branch collapse

**Ticket ID:** implement-finalization-logic

**Critical:** true

**Dependencies:** core-state-machine, create-git-operations

**Coordination Role:** Produces final clean epic branch for PR review

## Description

As a developer, I want epic finalization logic that collapses all completed ticket branches into the epic branch so that the epic produces a clean git history with one commit per ticket ready for PR review.

This ticket enhances the _finalize_epic() method in state_machine.py (ticket: core-state-machine) to implement the collapse phase that runs after all tickets complete. Uses GitOperations (ticket: create-git-operations) for merging. The finalization phase performs topological sort of tickets, squash-merges each into epic branch in dependency order, deletes ticket branches, and pushes epic branch to remote. Key logic to implement:
- _finalize_epic() -> Dict[str, Any]: Verify all tickets in terminal states (COMPLETED, BLOCKED, FAILED), transition epic to MERGING, call _topological_sort to get ordered ticket list, for each ticket call context.git.merge_branch(source=ticket.branch_name, target=epic_branch, strategy="squash", message=f"feat: {ticket.title}\n\nTicket: {ticket.id}"), append merge_commit to list, catch GitError (merge conflict) and fail epic with error, delete ticket branches via context.git.delete_branch(branch_name, remote=True), push epic branch via context.git.push_branch(epic_branch), transition epic to FINALIZED, return success dict
- _topological_sort(tickets: List[Ticket]) -> List[Ticket]: Sort tickets in dependency order (dependencies before dependents)

## Acceptance Criteria

- Tickets merged in dependency order via topological sort
- Each ticket squash-merged into epic branch with commit message format "feat: {title}\n\nTicket: {id}"
- Merge conflicts detected and cause epic to transition to FAILED state
- All ticket branches deleted after successful merge (both local and remote)
- Epic branch pushed to remote at end
- Epic state transitions to FINALIZED on success
- Returns dict with success=True, epic_branch, merge_commits, pushed=True

## Testing

Unit tests for _topological_sort with various dependency graphs including linear, diamond, and complex. Unit tests for _finalize_epic with mocked git operations. Integration tests with 3-5 ticket epics creating real stacked branches and merging them. Coverage: 85% minimum.

## Non-Goals

No interactive merge conflict resolution, no merge commit message customization, no partial merge state preservation, no cherry-picking.
