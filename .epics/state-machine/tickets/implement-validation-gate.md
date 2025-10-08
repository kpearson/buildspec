# Implement Validation Gate

## Description
Implement ValidationGate to validate LLM work before marking COMPLETED

## Dependencies
- create-gate-interface-and-protocol
- implement-git-operations-wrapper

## Acceptance Criteria
- [ ] ValidationGate checks branch has commits beyond base
- [ ] Checks final commit exists and is on branch
- [ ] Checks test suite status (passing or skipped for non-critical)
- [ ] Checks all acceptance criteria are met
- [ ] Returns GateResult with passed=True if all checks pass
- [ ] Returns GateResult with passed=False and reason if any check fails
- [ ] Critical tickets must have passing tests
- [ ] Non-critical tickets can skip tests

## Files to Modify
- /Users/kit/Code/buildspec/epic/gates.py
