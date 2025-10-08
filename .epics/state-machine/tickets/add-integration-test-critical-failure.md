# Add Integration Test Critical Failure

## Description
Add integration test for critical ticket failure with rollback

## Dependencies
- add-integration-test-happy-path

## Acceptance Criteria
- [ ] Test creates epic with critical ticket that fails
- [ ] Test verifies epic state transitions to FAILED
- [ ] Test verifies dependent tickets are BLOCKED
- [ ] Test verifies rollback is triggered if configured
- [ ] Test verifies state is preserved correctly

## Files to Modify
- /Users/kit/Code/buildspec/tests/epic/test_integration.py
