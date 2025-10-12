# ValidationGate for comprehensive work verification

**Ticket ID:** implement-validation-gate

**Critical:** true

**Dependencies:** create-gate-interface, create-git-operations, create-state-models

**Coordination Role:** Enforces quality standards and completeness for state machine

## Description

As a state machine developer, I want a comprehensive ValidationGate that verifies Claude builder work meets all requirements so that only validated, tested, working tickets transition to COMPLETED state.

This ticket creates the ValidationGate class in gates.py implementing the TransitionGate protocol (ticket: create-gate-interface). The state machine (ticket: core-state-machine) runs this gate during AWAITING_VALIDATION → COMPLETED transition (in _complete_ticket method). The gate runs multiple validation checks using GitOperations (ticket: create-git-operations) for git validation. This is the critical quality gate preventing incomplete work from being marked complete. Key functions to implement:
- check(ticket: Ticket, context: EpicContext) -> GateResult: Runs [_check_branch_has_commits, _check_final_commit_exists, _check_tests_pass, _check_acceptance_criteria], returns first failure or GateResult(passed=True) if all pass
- _check_branch_has_commits(ticket, context) -> GateResult: Calls context.git.get_commits_between(ticket.git_info.base_commit, ticket.git_info.branch_name), if len(commits) == 0 return failure "No commits on ticket branch", else return success with metadata
- _check_final_commit_exists(ticket, context) -> GateResult: Calls context.git.commit_exists(ticket.git_info.final_commit), then context.git.commit_on_branch(final_commit, branch_name), returns failure if either check fails
- _check_tests_pass(ticket, context) -> GateResult: If ticket.test_suite_status == "passing" return success, if "skipped" and not ticket.critical return success with metadata, else return failure with reason
- _check_acceptance_criteria(ticket, context) -> GateResult: If no criteria return success, find unmet criteria where ac.met == False, if any unmet return failure listing them, else return success

## Acceptance Criteria

- All validation checks implemented and run in sequence
- Returns passed=True only if ALL checks pass
- Returns clear failure reason identifying which check failed
- Critical tickets must have passing tests (not skipped)
- Non-critical tickets can have skipped tests
- Empty acceptance criteria list is valid (no-op check)
- Commits verified to exist and be on correct branch

## Testing

Unit tests for each validation check with passing and failing scenarios. Test with various test_suite_status values, acceptance criteria states, commit existence combinations. Coverage: 95% minimum.

## Non-Goals

No merge conflict checking (happens in finalize phase), no code quality analysis, no linting, no test re-running (trust builder's test_status), no performance benchmarks.
