# add-integration-test-crash-recovery

## Description
Add integration test for resuming epic execution after crash

## Epic Context
This test validates the resumability objective - that the state machine can recover from crashes and continue execution from the exact point of failure using the persisted state file.

**Key Objectives**:
- Resumability: State machine can resume from epic-state.json after crashes
- Auditable Execution: State file contains all information needed to resume

**Key Constraints**:
- State machine can resume mid-epic execution from state file
- State file is always in sync with actual execution state

## Acceptance Criteria
- Test starts epic execution, completes one ticket
- Test simulates crash by stopping state machine
- Test creates new state machine instance with resume=True
- Test verifies state is loaded from epic-state.json
- Test continues execution from where it left off
- Test validates all tickets complete successfully
- Test validates final epic state is FINALIZED

## Dependencies
- add-integration-test-happy-path

## Files to Modify
- /Users/kit/Code/buildspec/tests/epic/test_integration.py

## Additional Notes
Crash recovery test flow:

1. **Setup and Initial Execution**:
   - Create test epic with 3 tickets (A, B, C)
   - Initialize state machine (sm1)
   - Execute ticket A to completion
   - Verify state file contains A.state = COMPLETED
   - Verify state file contains A.git_info with final_commit

2. **Simulate Crash**:
   - Delete state machine instance (sm1)
   - State file remains on disk

3. **Resume Execution**:
   - Create new state machine instance (sm2) with resume=True
   - Verify sm2 loads state from epic-state.json
   - Verify sm2.tickets["A"].state = COMPLETED
   - Verify sm2.tickets["A"].git_info matches persisted data

4. **Continue Execution**:
   - get_ready_tickets() returns [B] (depends on A, which is COMPLETED)
   - Execute tickets B and C normally
   - Finalize epic

5. **Verify Final State**:
   - All tickets COMPLETED
   - Epic state FINALIZED
   - Git structure is identical to non-crashed execution

This test ensures the state machine can survive crashes and resume seamlessly, which is critical for long-running epic executions.
