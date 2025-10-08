# Add Integration Test Happy Path

## Description
Add integration test for happy path (3 tickets, all succeed, finalize)

## Dependencies
- add-state-machine-unit-tests

## Acceptance Criteria
- [ ] Test creates test epic with 3 sequential tickets
- [ ] Test initializes state machine
- [ ] Test executes all tickets synchronously
- [ ] Test validates stacked branches are created correctly
- [ ] Test validates tickets transition through all states
- [ ] Test validates finalize merges all tickets into epic branch
- [ ] Test validates epic branch is pushed to remote
- [ ] Test validates ticket branches are deleted
- [ ] Test uses real git repository (not mocked)

## Files to Modify
- /Users/kit/Code/buildspec/tests/epic/test_integration.py
