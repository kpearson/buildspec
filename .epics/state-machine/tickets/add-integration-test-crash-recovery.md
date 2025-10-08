# Add Integration Test Crash Recovery

## Description
Add integration test for resuming epic execution after crash

## Dependencies
- add-integration-test-happy-path

## Acceptance Criteria
- [ ] Test starts epic execution, completes one ticket
- [ ] Test simulates crash by stopping state machine
- [ ] Test creates new state machine instance with resume=True
- [ ] Test verifies state is loaded from epic-state.json
- [ ] Test continues execution from where it left off
- [ ] Test validates all tickets complete successfully
- [ ] Test validates final epic state is FINALIZED

## Files to Modify
- /Users/kit/Code/buildspec/tests/epic/test_integration.py
