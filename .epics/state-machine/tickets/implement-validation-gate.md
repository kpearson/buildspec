# implement-validation-gate

## Description
Implement ValidationGate to validate LLM work before marking COMPLETED

## Epic Context
This gate validates that the LLM has successfully completed the ticket before allowing the state transition to COMPLETED. It checks git commits, test results, and acceptance criteria.

**Key Objectives**:
- Validation Gates: Automated checks before allowing state transitions (branch exists, tests pass, etc.)
- LLM Interface Boundary: Clear contract between state machine (coordinator) and LLM (worker)
- Deterministic State Transitions: Python code enforces state machine rules, LLM cannot bypass gates

**Key Constraints**:
- Validation gates automatically verify LLM work before accepting state transitions
- Critical tickets must pass all validation checks

## Acceptance Criteria
- ValidationGate checks branch has commits beyond base
- Checks final commit exists and is on branch
- Checks test suite status (passing or skipped for non-critical)
- Checks all acceptance criteria are met
- Returns GateResult with passed=True if all checks pass
- Returns GateResult with passed=False and reason if any check fails
- Critical tickets must have passing tests
- Non-critical tickets can skip tests

## Dependencies
- create-gate-interface-and-protocol
- implement-git-operations-wrapper

## Files to Modify
- /Users/kit/Code/buildspec/epic/gates.py

## Additional Notes
This gate runs multiple validation checks:

1. **Commits Exist**: Verifies the branch has commits beyond the base_commit, indicating work was done
2. **Final Commit Valid**: Checks that the reported final_commit exists and is on the ticket's branch
3. **Test Status**: For critical tickets, requires test_suite_status = "passing". Non-critical tickets can have "skipped" or "passing"
4. **Acceptance Criteria**: Verifies all acceptance criteria are marked as met

The gate should return detailed failure reasons, listing all failed checks. This helps the LLM understand what needs to be fixed.

Critical vs non-critical distinction is important: critical ticket failures should fail the entire epic, while non-critical failures can be tolerated.
