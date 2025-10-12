# Epic rollback for critical failure cleanup

**Ticket ID:** implement-rollback-logic

**Critical:** false

**Dependencies:** implement-failure-handling, create-git-operations

**Coordination Role:** Provides cleanup semantics for critical failures

## Description

As a developer, I want epic rollback logic that cleans up branches and resets state when critical tickets fail so that failed epics leave no artifacts and can be restarted cleanly.

This ticket creates _execute_rollback() method in state_machine.py (ticket: core-state-machine) and updates _handle_ticket_failure() (ticket: implement-failure-handling) to call it when rollback_on_failure=true. Uses GitOperations (ticket: create-git-operations) for cleanup. Rollback deletes all ticket branches and resets epic branch to baseline commit. Key logic to implement:
- _execute_rollback(): Log rollback start, iterate all tickets with git_info, call context.git.delete_branch(ticket.git_info.branch_name, remote=True) for each, catch GitError and log warning (continue), reset epic branch to baseline via "git reset --hard {baseline_commit}", force push epic branch or delete if no prior work, transition epic to ROLLED_BACK, save state, log rollback complete

## Acceptance Criteria

- All ticket branches deleted on rollback (both local and remote)
- Epic branch reset to baseline commit
- Epic state transitioned to ROLLED_BACK
- Rollback only triggered for critical failures when epic.rollback_on_failure=true
- Rollback is idempotent (safe to call multiple times)
- Branch deletion failures logged but don't stop rollback

## Testing

Unit tests with mocked git operations verifying delete_branch called for each ticket, reset performed, state transitioned. Integration test with critical failure triggering rollback, verify branches deleted from real git repo. Coverage: 85% minimum.

## Non-Goals

No partial rollback, no rollback to specific ticket, no backup preservation, no rollback history tracking.
